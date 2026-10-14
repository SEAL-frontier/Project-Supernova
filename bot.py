from dotenv import load_dotenv
load_dotenv()
from minecraft_agent.v2 import VERSION
from minecraft_agent.v2.application import main

if __name__=='__main__':
    import os
    if os.environ.get('KEI_GATEWAY_ENABLED','1')=='1':main()
    else:print(f'keys-keys {VERSION}: Discord gateway disabled (KEI_GATEWAY_ENABLED=0).')
