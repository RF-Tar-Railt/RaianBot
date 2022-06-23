from app import RaianMain, load_config

bot = RaianMain(load_config('bot_config.yml'), debug_log=True)

if __name__ == '__main__':
    bot.load_plugins()
    bot.init_group_report()
    bot.init_announcement()
    bot.init_member_change_report()
    bot.init_start_report()
    bot.init_exception_report()
    bot.init_request_report()
    bot.init_greet()
    bot.running_sync()
