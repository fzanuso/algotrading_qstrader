import datetime
import click
import numpy as np
from qstrader import settings
from qstrader.compat import queue
from qstrader.price_parser import PriceParser
from qstrader.price_handler.yahoo_daily_csv_bar import YahooDailyCsvBarPriceHandler
from qstrader.strategy.base import Strategies
from qstrader.position_sizer.naive import NaivePositionSizer
from qstrader.risk_manager.example import ExampleRiskManager
from qstrader.portfolio_handler import PortfolioHandler
from qstrader.compliance.example import ExampleCompliance
from qstrader.execution_handler.ib_simulated import IBSimulatedExecutionHandler
from qstrader.statistics.tearsheet import TearsheetStatistics
from qstrader.trading_session import TradingSession
from strategies.coint_bollinger_strategy import CointegrationBollingerBandsStrategy


def run(config, testing, tickers, filename):
    # Set up variables needed for backtest
    events_queue = queue.Queue()
    csv_dir = config.CSV_DATA_DIR
    initial_equity = PriceParser.parse(500000.00)

    # Use Yahoo Daily Price Handler
    start_date = datetime.datetime(2015, 1, 1)
    end_date = datetime.datetime(2016, 9, 1)

    price_handler = YahooDailyCsvBarPriceHandler(
        csv_dir=csv_dir,
        events_queue=events_queue,
        init_tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        calc_adj_returns=False
    )

    # Use the Cointegration Bollinger Bands trading strategy
    weights = np.array([1.0, -1.213])
    lookback = 15
    entry_z = 1.5
    exit_z = 0.5
    base_quantity = 10000
    strategy = CointegrationBollingerBandsStrategy(
        tickers=tickers,
        events_queue=events_queue,
        lookback=lookback,
        weights=weights,
        entry_z=entry_z,
        exit_z=exit_z,
        base_quantity=base_quantity
    )
    strategy = Strategies(strategy)

    # Use the Naive Position Sizer
    # where suggested quantities are followed
    position_sizer = NaivePositionSizer()

    # Use an example Risk Manager
    risk_manager = ExampleRiskManager()

    # Use the default Portfolio Handler
    portfolio_handler = PortfolioHandler(
        initial_cash=initial_equity,
        events_queue=events_queue,
        price_handler=price_handler,
        position_sizer=position_sizer,
        risk_manager=risk_manager
    )

    # Use the ExampleCompliance component
    compliance = ExampleCompliance(config)

    # Use a simulated IB Execution Handler
    execution_handler = IBSimulatedExecutionHandler(
        events_queue, price_handler, compliance
    )
    # Use the Tearsheet Statistics
    title = ["Aluminum Smelting Strategy - ARNC/UNG"]
    statistics = TearsheetStatistics(config, portfolio_handler, title)

    # Set up the backtest
    backtest = TradingSession(
        config=config,
        tickers=tickers,
        equity=initial_equity,
        start_date=start_date,
        end_date=end_date,
        events_queue=events_queue,
        title=title,
        price_handler=price_handler,
        strategy=strategy,
        portfolio_handler=portfolio_handler,
        execution_handler=execution_handler,
        position_sizer=position_sizer,
        risk_manager=risk_manager,
        statistics=statistics,
    )

    results = backtest.start_trading(testing=testing)
    statistics.save(filename)

    return results


@click.command()
@click.option('--config', default='./config.yaml', help='Config filename')
@click.option('--testing/--no-testing', default=False, help='Enable testing mode')
@click.option('--tickers', default='SPY', help='Tickers (use comma)')
@click.option('--filename', default='', help='Pickle (.pkl) statistics filename')
def main(config, testing, tickers, filename):
    tickers = tickers.split(",")
    config = settings.from_file(config, testing)
    run(config, testing, tickers, filename)


if __name__ == "__main__":
    main()
