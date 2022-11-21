from app import launch, load_config

load_config(file='bot_config.yml')


if __name__ == '__main__':
    launch(debug_log=True)
