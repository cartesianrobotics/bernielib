import logging

#log = logging.getLogger('test_log')
#log.setLevel(logging.INFO)
#
#fh = logging.FileHandler('test1.log')
#fh.setLevel(logging.INFO)

#log.addHandler(fh)

logging.basicConfig(
                    filename='test.log',
                    #filename=(str(time.time())+'_calibrate.log'), 
                    #encoding='utf-8', 
                    level=logging.INFO,
                    format="%(asctime)s %(name)s:%(levelname)s:%(message)s",
                    )

if __name__ == '__main__':
    logging.info("Logging test.")