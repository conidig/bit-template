# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


import time
import aiohttp
import asyncio

# Bittensor
import bittensor as bt

# import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron

# Bittensor Validator Template:
from template.validator import forward


class Validator(BaseValidatorNeuron):
    """
    Your validator neuron class. You should use this class to define your validator's behavior. In particular, you should replace the forward function with your own logic.

    This class inherits from the BaseValidatorNeuron class, which in turn inherits from BaseNeuron. The BaseNeuron class takes care of routine tasks such as setting up wallet, subtensor, metagraph, logging directory, parsing config, etc. You can override any of the methods in BaseNeuron if you need to customize the behavior.

    This class provides reasonable default behavior for a validator such as keeping a moving average of the scores of the miners and using them to set weights at the end of each epoch. Additionally, the scores are reset for new hotkeys at the end of each epoch.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        bt.logging.info("load_state()")
        self.load_state()
        self.endpoint_url = "http://71.158.89.73:4437/get_work"

    async def query_endpoint(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.endpoint_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    bt.logging.error(f"Failed to query endpoint: {response.status}")
                    return None

    async def send_work_to_miners(self, work_data, request_id, timestamp, validator_hotkey):
        bt.logging.info(f"Sending work to miners: Request ID: {request_id}")

        for uid in self.metagraph.uids:
            bt.logging.info(f"Sending work to miner {uid}")

            await asyncio.sleep(0.1)

            bt.logging.info(f"Received response from miner {uid}")

        bt.logging.info("Finished sending work to all miners")

    async def forward(self):
        """
        Validator forward pass. Consists of:
        - Querying the endpoint for work
        - Processing the received data
        - Sending the work to miners
        - Getting the responses
        - Rewarding the miners
        - Updating the scores
        """
        work_data = await self.query_endpoint()

        if work_data is None:
            bt.logging.error("Failed to get work from endpoint")
            return

        request_id = work_data.get('request_id')
        timestamp = work_data.get('timestamp')
        validator_hotkey = self.wallet.hotkey.ss58_address

        bt.logging.info(f"Received work data: Request ID: {request_id}, Timestamp: {timestamp}, Validator Hotkey: {validator_hotkey}")

        await self.send_work_to_miners(work_data, request_id, timestamp, validator_hotkey)

        return await forward(self)

# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    with Validator() as validator:
        while True:
            bt.logging.info(f"Validator running... {time.time()}")
            time.sleep(5)


# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    with Validator() as validator:
        while True:
            bt.logging.info(f"Validator running... {time.time()}")
            time.sleep(5)
