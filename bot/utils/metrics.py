from bot.data_update import update_or_create
from bot.database.models import (
    BasicMetrics,
    TopAndBottom,
    MarketMetrics,
    FundsProfit,
    ManipulativeMetrics,
    NetworkMetrics,
    InvestingMetrics,
    SocialMetrics,
    Project
)
from bot.handlers.calculate import if_exist_instance
from bot.utils.consts import tickers


def update_project(session, user_coin_name, chosen_project):
    if user_coin_name not in tickers:
        return update_or_create(
            session, Project,
            defaults={'project_name': chosen_project},
            coin_name=user_coin_name
        )
    else:
        return session.query(Project).filter_by(coin_name=user_coin_name).first()


def update_social_metrics(session, project_id, social_metrics):
    if social_metrics:
        twitter_subs, twitter_twitterscore = social_metrics[0]
        update_or_create(
            session, SocialMetrics,
            defaults={
                'twitter': twitter_subs,
                'twitterscore': twitter_twitterscore
            },
            project_id=project_id
        )


def update_investing_metrics(session, project_id, investing_metrics, user_coin_name, investors):
    if investing_metrics:
        fundraise, fund_tier = investing_metrics[0]
        if user_coin_name not in tickers and fundraise and investors:
            update_or_create(
                session, InvestingMetrics,
                defaults={'fundraise': fundraise, 'fund_level': investors},
                project_id=project_id
            )
        elif fundraise:
            update_or_create(
                session, InvestingMetrics,
                defaults={'fundraise': fundraise},
                project_id=project_id
            )


def update_network_metrics(session, project_id, network_metrics, price, total_supply):
    if network_metrics:
        last_tvl = network_metrics[0]
        if last_tvl and price and total_supply:
            update_or_create(
                session, NetworkMetrics,
                defaults={
                    'tvl': last_tvl,
                    'tvl_fdv': last_tvl / (price * total_supply) if price * total_supply else 0
                },
                project_id=project_id
            )


def update_manipulative_metrics(session, project_id, manipulative_metrics, price, total_supply, fundraise):
    if manipulative_metrics:
        top_100_wallets = manipulative_metrics[0]
        update_or_create(
            session, ManipulativeMetrics,
            defaults={
                'fdv_fundraise': (price * total_supply) / fundraise if fundraise else None,
                'top_100_wallet': top_100_wallets
            },
            project_id=project_id
        )


def update_funds_profit(session, project_id, funds_profit_data):
    output_string = '\n'.join(funds_profit_data[0]) if funds_profit_data and funds_profit_data[0] else ''
    if output_string:
        update_or_create(
            session, FundsProfit,
            defaults={'distribution': output_string},
            project_id=project_id
        )


def update_market_metrics(session, project_id, market_metrics):
    if market_metrics:
        fail_high, growth_low, max_price, min_price = market_metrics[0]
        if all([fail_high, growth_low, max_price, min_price]):
            update_or_create(
                session, MarketMetrics,
                defaults={'fail_high': fail_high, 'growth_low': growth_low},
                project_id=project_id
            )
            update_or_create(
                session, TopAndBottom,
                defaults={'lower_threshold': min_price, 'upper_threshold': max_price},
                project_id=project_id
            )


def process_metrics(
        session,
        user_coin_name,
        chosen_project,
        results,
        price,
        total_supply,
        fundraise,
        investors
):
    new_project = update_project(session, user_coin_name, chosen_project)

    update_or_create(
        session, BasicMetrics,
        defaults={
            'entry_price': price,
            'sphere': chosen_project,
            'market_price': price
        },
        project_id=new_project.id
    )

    update_social_metrics(session, new_project.id, results.get("social_metrics"))
    update_investing_metrics(session, new_project.id, results.get("investing_metrics"), user_coin_name, investors)
    update_network_metrics(session, new_project.id, results.get("network_metrics"), price, total_supply)
    update_manipulative_metrics(session, new_project.id, results.get("manipulative_metrics"), price, total_supply, fundraise)
    update_funds_profit(session, new_project.id, results.get("funds_profit"))
    update_market_metrics(session, new_project.id, results.get("market_metrics"))

    return new_project


def check_missing_fields(metrics_data, fields_map):
    """
    Проверяет наличие данных в метриках и формирует список недостающих полей и примеров.
    """
    missing_fields = []
    examples = []

    for field_key, field_description in fields_map.items():
        if not metrics_data.get(field_key):
            missing_fields.append(field_description)
            examples.append(f"- {field_description}: <значение>")

    return missing_fields, examples


def generate_cells_content(
        basic_metrics_data_list,
        invested_metrics_data_list,
        social_metrics_data_list,
        market_metrics_data_list,
        manipulative_metrics_data_list,
        network_metrics_data_list,
        top_and_bottom_data_list,
        project,
        header_set,
        headers_mapping,
        tokenomics,
        cells_content
):
    basic_metrics = next((bm for bm in basic_metrics_data_list if bm[0] == project), None)
    investing_metrics = next((im for im in invested_metrics_data_list if im[0] == project), None)
    social_metrics = next((sm for sm in social_metrics_data_list if sm[0] == project), None)
    market_metrics = next((mm for mm in market_metrics_data_list if mm[0] == project), None)
    manipulative_metrics = next((man for man in manipulative_metrics_data_list if man[0] == project), None)
    network_metrics = next((nm for nm in network_metrics_data_list if nm[0] == project), None)
    top_and_bottom = next((km for km in top_and_bottom_data_list if km[0] == project), None)

    if header_set == headers_mapping[0]:
        cells_content = [
            project.coin_name,
            basic_metrics[1][0].sphere if basic_metrics[1][0].sphere else "-",
            f"{round(basic_metrics[1][0].market_price, 2)}$" if basic_metrics[1][0].market_price else 0,
            f"{round(investing_metrics[1][0].fundraise)}$" if if_exist_instance(investing_metrics, investing_metrics[1][0].fundraise) else "0"
        ]

    elif header_set == headers_mapping[1]:
        cells_content = [
            project.coin_name,
            investing_metrics[1][0].fund_level if if_exist_instance(investing_metrics, investing_metrics[1][0].fund_level) else "-"
        ]

    elif header_set == headers_mapping[2]:
        cells_content = [
            project.coin_name,
            str(social_metrics[1][0].twitter) if if_exist_instance(social_metrics, social_metrics[1][0].twitter) else "-",
            str(social_metrics[1][0].twitterscore) if if_exist_instance(social_metrics, social_metrics[1][0].twitterscore) else "-"
        ]

    elif header_set == headers_mapping[3]:
        cells_content = [
            project.coin_name,
            f"{round(tokenomics.capitalization)}$" if tokenomics and tokenomics.capitalization is not None else "-",
            f"{round(tokenomics.circ_supply, 2)}" if tokenomics and tokenomics.circ_supply is not None else "-",
            f"{round(tokenomics.total_supply, 2)}" if tokenomics and tokenomics.total_supply is not None else "-",
            f"{round(tokenomics.fdv, 2)}$" if tokenomics and tokenomics.fdv is not None else "-"
        ]

    elif header_set == headers_mapping[4]:
        cells_content = [
            project.coin_name,
            f"{round(market_metrics[1][0].fail_high * 100, 2)}%" if if_exist_instance(market_metrics, market_metrics[1][0].fail_high) else "-",
            f"x{round(market_metrics[1][0].growth_low, 2)}" if if_exist_instance(market_metrics, market_metrics[1][0].growth_low) else "-"
        ]

    elif header_set == headers_mapping[5]:
        cells_content = [
            project.coin_name,
            str(manipulative_metrics[1][0].fdv_fundraise) if if_exist_instance(manipulative_metrics, manipulative_metrics[1][0].fdv_fundraise) else "-",
            f"{round(manipulative_metrics[1][0].top_100_wallet * 100)}%" if if_exist_instance(manipulative_metrics, manipulative_metrics[1][0].top_100_wallet) else "-",
            str(network_metrics[1][0].tvl) if if_exist_instance(network_metrics, network_metrics[1][0].tvl) else "-",
            f"{round(network_metrics[1][0].tvl_fdv * 100)}%" if if_exist_instance(network_metrics, network_metrics[1][0].tvl_fdv) else "-",
            f"{top_and_bottom[1][0].lower_threshold}$" if if_exist_instance(top_and_bottom, top_and_bottom[1][0].lower_threshold) else "-",
            f"{top_and_bottom[1][0].upper_threshold}$" if if_exist_instance(top_and_bottom, top_and_bottom[1][0].upper_threshold) else "-"
        ]

    return cells_content


def create_project_data_row(
        project,
        tokenomics,
        basic_metrics,
        investing_metrics,
        social_metrics,
        market_metrics,
        manipulative_metrics,
        network_metrics,
        top_and_bottom
):
    return [
        project.coin_name,
        project.project_name if project.project_name else "-",
        f"{round(basic_metrics[1][0].market_price, 2)}$" if if_exist_instance(basic_metrics, basic_metrics[1][0].market_price) else "-",
        f"{round(investing_metrics[1][0].fundraise)}$" if if_exist_instance(investing_metrics, investing_metrics[1][0].fundraise) else "-",
        investing_metrics[1][0].fund_level if if_exist_instance(investing_metrics, investing_metrics[1][0].fund_level) else "-",
        social_metrics[1][0].twitter if if_exist_instance(social_metrics, social_metrics[1][0].twitter) else "-",
        social_metrics[1][0].twitterscore if if_exist_instance(social_metrics, social_metrics[1][0].twitterscore) else "-",
        f"{round(tokenomics.capitalization)}$" if tokenomics.capitalization else "-",
        round(tokenomics.circ_supply, 2) if tokenomics.circ_supply else "-",
        round(tokenomics.total_supply, 2) if tokenomics.total_supply else "-",
        f"{round(tokenomics.fdv, 2)}$" if tokenomics.fdv else "-",
        f"{round(market_metrics[1][0].fail_high * 100, 2)}%" if if_exist_instance(market_metrics, market_metrics[1][0].fail_high) else "-",
        f"x{round(market_metrics[1][0].growth_low)}" if if_exist_instance(market_metrics, market_metrics[1][0].growth_low) else "-",
        manipulative_metrics[1][0].fdv_fundraise if if_exist_instance(manipulative_metrics, manipulative_metrics[1][0].fdv_fundraise) else "-",
        f"{round(manipulative_metrics[1][0].top_100_wallet * 100)}%" if if_exist_instance(manipulative_metrics, manipulative_metrics[1][0].top_100_wallet) else "-",
        network_metrics[1][0].tvl if if_exist_instance(network_metrics, network_metrics[1][0].tvl) else "-",
        f"{round(network_metrics[1][0].tvl_fdv * 100)}%" if if_exist_instance(network_metrics, network_metrics[1][0].tvl_fdv) else "-",
        f"{top_and_bottom[1][0].lower_threshold}$" if if_exist_instance(top_and_bottom, top_and_bottom[1][0].lower_threshold) else "-",
        f"{top_and_bottom[1][0].upper_threshold}$" if if_exist_instance(top_and_bottom, top_and_bottom[1][0].upper_threshold) else "-"
    ]
