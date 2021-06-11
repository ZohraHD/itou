"""
Populate metabase with fluxIAE data and some custom tables for our needs (mainly `missions_ai_ehpad`).

For itou data, see the other script `populate_metabase.py`.

At this time this script is only supposed to run manually on your local dev, not in production.

It manipulates large dataframes in memory (~10M rows) and thus is not optimized for production low memory environment.

This script takes ~2 hours to complete.

Refactoring it for low memory use would make it even longer and is actually not trivial. It might be attempted though.

1) Vocabulary.

- aka = also known as
- sme = suivi mensuel
- dsm = détail suivi mensuel
- emi = état mensuel individuel (AFAIU same as `dsm`)
- mei = mission état (mensuel) individuel
- ctr = contrat
- mis = mission

2) Basic fluxIAE models.

Structure
~5K

Contract
No dedicated table so the total number of contracts is unknown but most likely ~1M based on other tables.

"Etat Mensuel Individuel" aka EMI aka DSM
~7M
Each month each employer inputs an EMI for each of their employees.
~20% of EMI are attached to a Mission.

Mission
~3M
Employers generally input their EMI without Mission, but sometimes, when they send their employees to another
employer, they do input a Mission attached to their EMI.

3) Advanced fluxIAE models acting as a relationship between two basic models.

Mission-EMI aka MEI
~3M
Store associations between EMI and Missions.

Contract-Mission
~1M
Store associations between Contracts and Missions.

4) Relationships between models.

One structure has many contracts.

One contract has many missions.

One mission has many EMI.

An EMI does not necessarily have a mission.

"""
import logging
import os
from collections import OrderedDict

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from psycopg2 import sql
from tqdm import tqdm

from itou.metabase.management.commands._database_psycopg2 import MetabaseDatabaseCursor
from itou.metabase.management.commands._database_sqlalchemy import get_pg_engine
from itou.siaes.management.commands._import_siae.utils import get_fluxiae_df, get_fluxiae_referential_filenames, timeit
from itou.siaes.models import Siae
from itou.utils.address.departments import DEPARTMENT_TO_REGION, DEPARTMENTS


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


if settings.METABASE_SHOW_SQL_REQUESTS:
    # Unfortunately each SQL query log appears twice ¬_¬
    mylogger = logging.getLogger("django.db.backends")
    mylogger.setLevel(logging.DEBUG)
    mylogger.addHandler(logging.StreamHandler())


class Command(BaseCommand):
    """
    Populate metabase database with fluxIAE data.

    The `dry-run` mode is useful for quickly testing changes and iterating.
    It builds tables with a *_dry_run suffix added to their name, to avoid
    touching any real table, and injects only a sample of data.

    To populate alternate tables with sample data:
        django-admin populate_metabase_fluxiae --verbosity=2 --dry-run

    When ready:
        django-admin populate_metabase_fluxiae --verbosity=2
    """

    help = "Populate metabase database with fluxIAE data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", dest="dry_run", action="store_true", help="Populate alternate tables with sample data"
        )

    def set_logger(self, verbosity):
        """
        Set logger level based on the verbosity option.
        """
        handler = logging.StreamHandler(self.stdout)

        self.logger = logging.getLogger(__name__)
        self.logger.propagate = False
        self.logger.addHandler(handler)

        self.logger.setLevel(logging.INFO)
        if verbosity > 1:
            self.logger.setLevel(logging.DEBUG)

    def log(self, message):
        self.logger.debug(message)

    def store_df(self, df, vue_name):
        """
        Store dataframe in database.

        Do this dataframe chunk by dataframe chunk to solve
        psycopg2.OperationalError "server closed the connection unexpectedly" error.
        """
        if self.dry_run:
            vue_name += "_dry_run"

        # Recipe from https://stackoverflow.com/questions/44729727/pandas-slice-large-dataframe-in-chunks
        rows_per_chunk = 10 * 1000
        df_chunks = [df[i : i + rows_per_chunk] for i in range(0, df.shape[0], rows_per_chunk)]

        self.log(f"Storing {len(df_chunks)} chunks of (max) {rows_per_chunk} rows each ...")
        if_exists = "replace"  # For the 1st chunk, drop old existing table if needed.
        for df_chunk in tqdm(df_chunks):
            pg_engine = get_pg_engine()
            df_chunk.to_sql(
                name=f"{vue_name}_new",
                # Use a new connection for each chunk to avoid random disconnections.
                con=pg_engine,
                if_exists=if_exists,
                index=False,
                chunksize=1000,
                # INSERT by batch and not one by one. Increases speed x100.
                method="multi",
            )
            pg_engine.dispose()
            if_exists = "append"  # For all other chunks, append to table in progress.

        self.switch_table_atomically(table_name=vue_name)
        self.log(f"Stored {vue_name} in database ({len(df)} rows).")
        self.log("")

    @timeit
    def populate_fluxiae_structures(self):
        """
        Populate fluxIAE_Structure table and enrich it with some itou data.
        """
        vue_name = "fluxIAE_Structure"
        df = get_fluxiae_df(
            vue_name=vue_name,
            converters={
                "structure_siret_actualise": str,
                "structure_siret_signature": str,
                "structure_adresse_mail_corresp_technique": str,
                "structure_adresse_gestion_cp": str,
                "structure_adresse_gestion_telephone": str,
            },
            dry_run=self.dry_run,
        )

        # Enrich Vue Structure with some itou data.
        for index, row in df.iterrows():
            asp_id = row["structure_id_siae"]
            siaes = Siae.objects.filter(source=Siae.SOURCE_ASP, convention__asp_id=asp_id).select_related("convention")

            # Preferably choose an AI.
            ai_siaes = [s for s in siaes if s.kind == Siae.KIND_AI]
            if len(ai_siaes) >= 1:
                siae = ai_siaes[0]
            else:
                siae = siaes.first()

            if siae:
                # row is a copy no longer connected to initial df.
                df.loc[index, "itou_name"] = siae.display_name
                df.loc[index, "itou_kind"] = siae.kind
                df.loc[index, "itou_post_code"] = siae.post_code
                df.loc[index, "itou_city"] = siae.city
                df.loc[index, "itou_department_code"] = siae.department
                df.loc[index, "itou_department"] = DEPARTMENTS.get(siae.department)
                df.loc[index, "itou_region"] = DEPARTMENT_TO_REGION.get(siae.department)
                df.loc[index, "itou_latitude"] = siae.latitude
                df.loc[index, "itou_longitude"] = siae.longitude

        self.store_df(df=df, vue_name=vue_name)

    @timeit
    def populate_fluxiae_view(self, vue_name, skip_first_row=True):
        df = get_fluxiae_df(vue_name=vue_name, skip_first_row=skip_first_row, dry_run=self.dry_run)
        self.store_df(df=df, vue_name=vue_name)

    def populate_fluxiae_referentials(self):
        for filename in get_fluxiae_referential_filenames():
            self.populate_fluxiae_view(vue_name=filename)

    def populate_departments(self):
        """
        Populate department codes, department names and region names.
        """
        rows = []

        for dpt_code, dpt_name in DEPARTMENTS.items():
            # We want to preserve the order of columns.
            row = OrderedDict()

            row["code_departement"] = dpt_code
            row["nom_departement"] = dpt_name
            row["nom_region"] = DEPARTMENT_TO_REGION[dpt_code]

            rows.append(row)

        # `columns=rows[0].keys()` trick is necessary to preserve the order of columns.
        df = pd.DataFrame(rows, columns=rows[0].keys())

        self.store_df(df=df, vue_name="departements")

    def switch_table_atomically(self, table_name):
        with MetabaseDatabaseCursor() as (cur, conn):
            cur.execute(
                sql.SQL("ALTER TABLE IF EXISTS {} RENAME TO {}").format(
                    sql.Identifier(table_name), sql.Identifier(f"{table_name}_old")
                )
            )
            cur.execute(
                sql.SQL("ALTER TABLE {} RENAME TO {}").format(
                    sql.Identifier(f"{table_name}_new"), sql.Identifier(table_name)
                )
            )
            conn.commit()
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(f"{table_name}_old")))
            conn.commit()

    def build_custom_table(self, table_name, sql_request):
        """
        Build a new table with given sql_request.
        Minimize downtime by building a temporary table first then swap the two tables atomically.
        """
        if self.dry_run:
            # Note that during a dry run, the dry run version of the current table will be built
            # from the wet run version of the underlying tables.
            table_name += "_dry_run"

        with MetabaseDatabaseCursor() as (cur, conn):
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(f"{table_name}_new")))
            conn.commit()
            cur.execute(
                sql.SQL("CREATE TABLE {} AS {}").format(sql.Identifier(f"{table_name}_new"), sql.SQL(sql_request))
            )
            conn.commit()

        self.switch_table_atomically(table_name=table_name)
        self.log("Done.")

    @timeit
    def build_custom_tables(self):
        """
        Build custom tables one by one by playing SQL requests in `sql` folder.

        Typically:
        - 001_fluxIAE_DateDerniereMiseAJour.sql
        - 002_missions_ai_ehpad.sql
        - ...

        The numerical prefixes ensure the order of execution is deterministic.

        The name of the table being created with the query is derived from the filename,
        # e.g. '002_missions_ai_ehpad.sql' => 'missions_ai_ehpad'
        """
        path = f"{CURRENT_DIR}/sql"
        for filename in [f for f in os.listdir(path) if f.endswith(".sql")]:
            self.log(f"Running {filename} ...")
            table_name = "_".join(filename.split(".")[0].split("_")[1:])
            with open(os.path.join(path, filename), "r") as file:
                sql_request = file.read()
            self.build_custom_table(table_name=table_name, sql_request=sql_request)

    @timeit
    def populate_metabase_fluxiae(self):
        if not settings.ALLOW_POPULATING_METABASE:
            self.log("Populating metabase is not allowed in this environment.")
            return

        self.populate_fluxiae_referentials()

        # Specific fluxIAE views requiring some mixing with itou data.
        self.populate_fluxiae_structures()

        # Regular fluxIAE views not mixed with any itou data.
        self.populate_fluxiae_view(vue_name="fluxIAE_AnnexeFinanciere")
        self.populate_fluxiae_view(vue_name="fluxIAE_ContratMission", skip_first_row=False)
        self.populate_fluxiae_view(vue_name="fluxIAE_Encadrement")
        self.populate_fluxiae_view(vue_name="fluxIAE_EtatMensuelAgregat")
        self.populate_fluxiae_view(vue_name="fluxIAE_EtatMensuelIndiv")
        self.populate_fluxiae_view(vue_name="fluxIAE_Formations")
        self.populate_fluxiae_view(vue_name="fluxIAE_Missions")
        self.populate_fluxiae_view(vue_name="fluxIAE_MissionsEtatMensuelIndiv")
        self.populate_fluxiae_view(vue_name="fluxIAE_PMSMP")
        self.populate_fluxiae_view(vue_name="fluxIAE_Salarie", skip_first_row=False)

        # Custom views for our needs (no fluxIAE data involved).
        self.populate_departments()

        # Build custom tables by running raw SQL queries on existing tables.
        self.build_custom_tables()

    def handle(self, dry_run=False, **options):
        self.set_logger(options.get("verbosity"))
        self.dry_run = dry_run
        self.populate_metabase_fluxiae()
        self.log("-" * 80)
        self.log("Done.")
