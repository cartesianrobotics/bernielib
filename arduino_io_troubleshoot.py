import bernielib as bl
import time

if __name__ == '__main__':
    ber = bl.robot()
    #ber.home()
    #ber.move(z=100)
    ber.writeAndWaitLoadCell('T')
    #time.sleep(0.2)
    message = ber.writeAndWaitLoadCell('RR')
    print(message)
