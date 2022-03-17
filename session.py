from argparse import ArgumentParser

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-e', '--exp_env', help='experimentation environment - disk to analyze')
    parser.add_argument('-s', '--size', help='size of file to be written (in MB)')

    print('[Starting the session..]')

    print('[..process finished, terminating the session ! \nMay the force be with you]')
    pass