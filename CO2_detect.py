#!/usr/bin/env python3.7

import os
import sys
from logging import basicConfig, getLogger, DEBUG, FileHandler, Formatter
from time import sleep

#import slack_notifier
from CCS811 import CCS811

class AirConditionMonitor:
    CO2_PPM_THRESHOLD_1 = 1000
    CO2_PPM_THRESHOLD_2 = 2000

    CO2_LOWER_LIMIT  =  400
    CO2_HIGHER_LIMIT = 8192

    CO2_STATUS_CONDITIONING = 'CONDITIONING'
    CO2_STATUS_LOW          = 'LOW'
    CO2_STATUS_HIGH         = 'HIGH'
    CO2_STATUS_TOO_HIGH     = 'TOO HIGH'
    CO2_STATUS_ERROR        = 'ERROR'

#    SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/XXXXXXXXX/XXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX'
#    SLACK_USERNAME    = 'AIR_CONDITION_MONITOR'
#    SLACK_EMOJI_ICON  = ':loudspeaker:'
#    SLACK_CHANNEL     = '#air_condition_monitor'

    LOG_FILE = '{script_dir}/logs/air_condition_monitor.log'.format(
        script_dir = os.path.dirname(os.path.abspath(__file__))
    )

    def __init__(self):
        self._ccs811 = CCS811()
#        self.slack_notifier = slack_notifier.SlackNotifier(self.SLACK_WEBHOOK_URL)
        self.co2_status = self.CO2_STATUS_LOW
        self.init_logger()

    def init_logger(self):
        self._logger = getLogger(__class__.__name__)
        file_handler = FileHandler(self.LOG_FILE)
        formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)
        self._logger.setLevel(DEBUG)

#    def notify_to_slack(self, co2, co2_status):
#        if co2_status == self.CO2_STATUS_ERROR:
#            fallback = "Something Went Wrong..."
#            text = fallback
#            color = 'danger'
#        else:
#            fallback = "CO2 level is {0}: {1:,}ppm".format(co2_status, co2)
#            text = fallback
#
#            color = 'good'
#            if co2_status == self.CO2_STATUS_HIGH:
#                color = 'warning'
#            elif co2_status == self.CO2_STATUS_TOO_HIGH:
#                color = 'danger'
#
#        res = self.slack_notifier.notify(
#            fallback, text, self.SLACK_USERNAME, self.SLACK_EMOJI_ICON, self.SLACK_CHANNEL, color
#        )
#        self._logger.debug(
#            'Notified to Slack. STATUS_CODE - {status_code}, MSG - {msg}'.format(
#                status_code = res['status_code'], msg = res['text']
#            )
#        )

    def status(self, co2):
        if co2 < self.CO2_LOWER_LIMIT or co2 > self.CO2_HIGHER_LIMIT:
            return self.CO2_STATUS_CONDITIONING
        elif co2 < self.CO2_PPM_THRESHOLD_1:
            return self.CO2_STATUS_LOW
        elif co2 < self.CO2_PPM_THRESHOLD_2:
            return self.CO2_STATUS_HIGH
        else:
            return self.CO2_STATUS_TOO_HIGH

    def execute(self):
        while not self._ccs811.available():
            pass

        while True:
            if not self._ccs811.available():
                sleep(1)
                continue

            try:
                if not self._ccs811.readData():
                    co2 = self._ccs811.geteCO2()
                    co2_status = self.status(co2)
                    if co2_status == self.CO2_STATUS_CONDITIONING:
                        self._logger.debug("STATUS: UnderConditioning...")
                        sleep(1200)
                        continue

                    if co2_status != self.co2_status:
#                        self.notify_to_slack(co2, co2_status)
                        self.co2_status = co2_status

                    self._logger.info("CO2: {0}ppm, TVOC: {1}".format(co2, self._ccs811.getTVOC()))
                else:
                    self._logger.error('ERROR!')
                    while True:
                        pass
            except:
                self._logger.error(sys.exc_info())
#                self.notify_to_slack(-1, self.CO2_STATUS_ERROR)

            sleep(60)

if __name__ == '__main__':
    air_condition_monitor = AirConditionMonitor()
    air_condition_monitor.execute()
