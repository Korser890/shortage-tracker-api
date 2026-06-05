import sys
from loguru import logger
from ingestion.eia_prices import run as run_eia_prices
from ingestion.eia_inventory import run as run_eia_inventory
from ingestion.fred_energy import run as run_fred_energy
from ingestion.eia_international import run as run_eia_international
from transformation.transform_prices import run as run_transform_prices
from transformation.transform_inventory import run as run_transform_inventory
from transformation.transform_international import run as run_transform_international
from ingestion.newsapi_headlines import run as run_newsapi_headlines
from transformation.transform_headlines import run as run_transform_headlines


from database.load import run as run_load


def run_ingestion():
    logger.info("--- Ingestion starting ---")
    try:
        run_eia_prices()
        run_eia_inventory()
        run_fred_energy()
        run_eia_international()
        run_newsapi_headlines()
        logger.info("--- Ingestion complete ---")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise




def run_transformation():
    logger.info("--- Transformation starting ---")
    try:
        run_transform_prices()
        run_transform_inventory()
        run_transform_international()
        run_transform_headlines()
        logger.info("--- Transformation complete ---")
    except Exception as e:
        logger.error(f"Transformation failed: {e}")
        raise



def load():
    logger.info("--- Load starting ---")
    try:
        run_load()
        logger.info("--- Load complete ---")
    except Exception as e:
        logger.error(f"Load failed: {e}")
        raise


def run():
    logger.info("========== Pipeline starting ==========")
    try:
        run_ingestion()
        run_transformation()
        load()
        logger.info("========== Pipeline complete ==========")
    except Exception as e:
        logger.error(f"Pipeline aborted: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()

