from app import RaianMain, bot_config

bot = RaianMain(bot_config, debug_log=True)
bot.load_plugins()
bot.init_group_report()
bot.init_announcement()
bot.init_member_change_report()
bot.init_start_report()
bot.init_exception_report()
bot.init_request_report()
bot.init_greet()
bot.running_sync()
