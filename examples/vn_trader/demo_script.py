from time import sleep

from vnpy.trader.constant import OrderType, Status

from vnpy.app.script_trader import ScriptEngine


def run(engine: ScriptEngine):
    """
    脚本策略的主函数说明：
    1. 唯一入参是脚本引擎ScriptEngine对象，通用它来完成查询和请求操作
    2. 该函数会通过一个独立的线程来启动运行，区别于其他策略模块的事件驱动
    3. while循环的维护，请通过engine.strategy_active状态来判断，实现可控退出

    脚本策略的应用举例：
    1. 自定义篮子委托执行执行算法
    2. 股指期货和一篮子股票之间的对冲策略
    3. 国内外商品、数字货币跨交易所的套利
    4. 自定义组合指数行情监控以及消息通知
    5. 股票市场扫描选股类交易策略（龙一、龙二）
    6. 等等~~~
    """
    vt_symbols = ["00700.SEHK"] #["01157.SEHK", "09922.SEHK" ] #["FB.SMART", "ZM.SMART"]# ["IF1912.CFFEX", "rb2001.SHFE"]

    # 订阅行情
    engine.subscribe(vt_symbols)

    # 获取合约信息
    for vt_symbol in vt_symbols:
        contract = engine.get_contract(vt_symbol)
        msg = f"合约信息，{contract}"
        engine.write_log(msg)

    # 持续运行，使用strategy_active来判断是否要退出程序
    while engine.strategy_active:
        # 轮询获取行情
        for vt_symbol in vt_symbols:
            tick = engine.get_tick(vt_symbol)
            msg = f"最新行情, {tick}"
            engine.write_log(msg)

            if tick is None:
                sleep(2)
                break

            if tick.symbol=='00700':
                volume = tick.volume
                open_interest = tick.open_interest
                last_price, last_volume = tick.last_price, tick.last_volume
                limit_up, limit_down = tick.limit_up, tick.limit_down
                open_price, high_price, low_price, pre_close = tick.open_price, tick.high_price, tick.low_price, tick.pre_close

                bid_price_1, bid_price_2, bid_price_3, bid_price_4, bid_price_5 = (
                    tick.bid_price_1, tick.bid_price_2, tick.bid_price_3, tick.bid_price_4, tick.bid_price_5)
                ask_price_1, ask_price_2, ask_price_3, ask_price_4, ask_price_5 = (
                    tick.ask_price_1, tick.ask_price_2, tick.ask_price_3, tick.ask_price_4, tick.ask_price_5)

                bid_volume_1, bid_volume_2, bid_volume_3, bid_volume_4, bid_volume_5 = (
                    tick.bid_volume_1, tick.bid_volume_2, tick.bid_volume_3, tick.bid_volume_4, tick.bid_volume_5)
                ask_volume_1, ask_volume_2, ask_volume_3, ask_volume_4, ask_volume_5 = (
                    tick.ask_volume_1, tick.ask_volume_2, tick.ask_volume_3, tick.ask_volume_4, tick.ask_volume_5)

                vt_orderid = engine.buy(vt_symbol="00700.SEHK",
                    price=limit_down,
                    volume=200,
                    order_type=OrderType.LIMIT
                )
                sleep(30)
                if vt_orderid:
                    order = engine.get_order(vt_orderid)
                    if order.status in (Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED):
                        engine.cancel_order(vt_orderid)
                    elif order.status in (Status.ALLTRADED, Status.CANCELLED, Status.REJECTED):
                        engine.write_log(f"Order {vt_orderid} is {order.status}")

                vt_orderid = engine.sell(vt_symbol="00700.SEHK",
                    price=limit_up,
                    volume=200,
                    order_type=OrderType.LIMIT
                )
                sleep(30)
                if vt_orderid:
                    order = engine.get_order(vt_orderid)
                    if order.status in (Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED):
                        engine.cancel_order(vt_orderid)
                    elif order.status in (Status.ALLTRADED, Status.CANCELLED, Status.REJECTED):
                        engine.write_log(f"Order {vt_orderid} is {order.status}")

        # 等待3秒进入下一轮
        sleep(3)
