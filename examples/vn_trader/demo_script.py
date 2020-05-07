from time import sleep, time

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
    max_volume = 2000.0
    take_profit = 0.04
    entry_price = 6.20
    exit_price = entry_price * 1.04
    order_fill_waiting_time = 3
    vt_symbols = ["01157.SEHK"] #["01157.SEHK", "09922.SEHK" ] #["FB.SMART", "ZM.SMART"]# ["IF1912.CFFEX", "rb2001.SHFE"]

    # 订阅行情
    engine.subscribe(vt_symbols)

    # 获取合约信息
    for vt_symbol in vt_symbols:
        contract = engine.get_contract(vt_symbol)
        msg = f"合约信息，{contract}"
        engine.write_log(msg)

    # 查询账户
    account = engine.get_account(vt_accountid="FUTU.FUTU_HK")
    print(f"Account: {account}")

    # 查询持仓
    # position = engine.get_position(vt_positionid='01810.SEHK.多')
    positions = engine.get_all_positions()
    print(f"Position: {positions}")

    # 持续运行，使用strategy_active来判断是否要退出程序
    while engine.strategy_active:
        # 轮询获取行情
        for vt_symbol in vt_symbols:
            symbol, exchange = vt_symbol.split(".")
            tick = engine.get_tick(vt_symbol)
            msg = f"最新行情, {tick}"
            engine.write_log(msg)

            if tick is None:
                sleep(2)
                break

            if tick.symbol==symbol:
                position = engine.get_position(vt_positionid=f'{vt_symbol}.多')

                # 如果已有头寸，则进行卖出操作
                if position:
                    cost = position.price * position.volume
                    if position.pnl / cost > take_profit:
                        vt_orderid = engine.sell(vt_symbol=vt_symbol,
                                                 price=tick.bid_price_1,
                                                 volume=position.volume,
                                                 order_type=OrderType.LIMIT
                                                 )

                        # 确认下单已经成功
                        if not vt_orderid:
                            c = input("下卖单失败，是否继续？")
                            if c not in ("Y", "y"):
                                engine.stop_strategy()
                                break

                        # 最多等待1分钟促使订单成交
                        now = time()
                        while (time()-now<60):
                            # 等待3秒让其成交
                            sleep(order_fill_waiting_time)
                            order = engine.get_order(vt_orderid)
                            # 如果不能成交，取消订单，再拿新价格重新发单
                            if order.status in (Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED):
                                engine.cancel_order(vt_orderid)
                                new_tick = engine.get_tick(vt_symbol=vt_symbol)
                                position = engine.get_position(vt_positionid=f'{vt_symbol}.多')
                                assert position is not None, "Position info mismatch!"
                                vt_orderid = engine.sell(vt_symbol=vt_symbol,
                                                         price=new_tick.bid_price_1,
                                                         volume=position.volume,
                                                         order_type=OrderType.LIMIT
                                                         )
                                engine.write_log(f"未能在{order_fill_waiting_time}秒内以价格{order.price}卖出，改单至新价格{new_tick.bid_price_1}")
                            # 如果已经成交，则继续
                            elif order.status in (Status.ALLTRADED, ):
                                engine.write_log(f"订单{vt_orderid}状态为{order.status}")
                                break
                            # 如果订单状态是取消或拒绝，终止策略
                            elif order.status in (Status.CANCELLED, Status.REJECTED):
                                engine.write_log(f"订单{vt_orderid}状态为{order.status}")
                                engine.write_log("终止策略。。。")
                                engine.stop_strategy()
                                break
                    else:
                        engine.write_log(f"未达至平仓条件position.pnl/cost={position.pnl}/{cost}={position.pnl/cost} < {take_profit}")
                # 如果无头寸，则进行买入操作
                else:
                    # 判断进入条件
                    if tick.ask_price_1>entry_price:
                        engine.write_log(f"卖1价{tick.ask_price_1}仍然高于设置的进入价{entry_price}")
                        break

                    # 买入
                    target_volume = min(tick.ask_volume_1, max_volume)
                    vt_orderid = engine.buy(vt_symbol=vt_symbol,
                        price=tick.ask_price_1,
                        volume=target_volume,
                        order_type=OrderType.LIMIT
                    )

                    # 确认下单已经成功
                    if not vt_orderid:
                        c = input("下买单失败，是否继续？")
                        if c not in ("Y", "y"):
                            engine.stop_strategy()
                            break

                    # 最多等待1分钟促使订单成交
                    now = time()
                    while (time() - now < 60):
                        # 等待3秒让其成交
                        sleep(order_fill_waiting_time)
                        order = engine.get_order(vt_orderid)
                        # 如果不能成交，取消订单，再拿新价格重新发单
                        if order.status in (Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED):
                            engine.cancel_order(vt_orderid)
                            new_tick = engine.get_tick(vt_symbol=vt_symbol)
                            position = engine.get_position(vt_positionid=f'{vt_symbol}.多')
                            if position is not None:
                                target_volume -= position.volume
                            vt_orderid = engine.buy(vt_symbol=vt_symbol,
                                                    price=new_tick.ask_price_1,
                                                    volume=target_volume,
                                                    order_type=OrderType.LIMIT
                                                    )
                            engine.write_log(
                                f"未能在{order_fill_waiting_time}秒内以价格{order.price}买入，改单至新价格{new_tick.bid_price_1}")
                        # 如果已经成交，则继续
                        elif order.status in (Status.ALLTRADED,):
                            engine.write_log(f"订单{vt_orderid}状态为{order.status}")
                            break
                        # 如果订单状态是取消或拒绝，终止策略
                        elif order.status in (Status.CANCELLED, Status.REJECTED):
                            engine.write_log(f"订单{vt_orderid}状态为{order.status}")
                            engine.write_log("终止策略。。。")
                            engine.stop_strategy()
                            break

        # 等待3秒进入下一轮
        sleep(3)
