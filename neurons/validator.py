# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


import time
import aiohttp
import asyncio
import requests
import argparse
import re

# Bittensor
import bittensor as bt

# Add these imports
import hashlib
import struct

# import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron

# Bittensor Validator Template:
from template.validator import forward
from template.protocol import WorkData

# Add a helper function for detailed logging
def detailed_log(message):
    if isinstance(message, dict):
        # Remove transaction-related keys
        cleaned_message = {k: v for k, v in message.items() if k not in ['transactions', 'data', 'hash', 'txid', 'fee', 'sigops', 'weight', 'depends']}
        bt.logging.info(f"[DETAILED] {cleaned_message}")
    else:
        # For non-dict messages, remove any transaction-like data
        cleaned_message = re.sub(r"'(data|hash|txid|fee|sigops|weight|depends)':\s*'?[^'}\n]*'?,?\s*", "", str(message))
        bt.logging.info(f"[DETAILED] {cleaned_message}")


class Validator(BaseValidatorNeuron):
    """
    Your validator neuron class. You should use this class to define your validator's behavior. In particular, you should replace the forward function with your own logic.

    This class inherits from the BaseValidatorNeuron class, which in turn inherits from BaseNeuron. The BaseNeuron class takes care of routine tasks such as setting up wallet, subtensor, metagraph, logging directory, parsing config, etc. You can override any of the methods in BaseNeuron if you need to customize the behavior.

    This class provides reasonable default behavior for a validator such as keeping a moving average of the scores of the miners and using them to set weights at the end of each epoch. Additionally, the scores are reset for new hotkeys at the end of each epoch.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        bt.logging.info("Initializing Validator")
        self.load_state()
        self.get_work_url = "http://71.158.89.73:4437/get_work"
        self.submit_work_url = "http://71.158.89.73:4437/submit_work"
        bt.logging.info(f"Get work URL: {self.get_work_url}")
        bt.logging.info(f"Submit work URL: {self.submit_work_url}")
        bt.logging.info(f"Validator config: {self.config}")
        bt.logging.info(f"Subtensor network: {self.subtensor.network}")
        bt.logging.info(f"Metagraph: {self.metagraph}")
        bt.logging.info(f"Axon config: {self.axon.config}")
        bt.logging.info(f"Axon external IP: {self.axon.external_ip}")
        bt.logging.info(f"Axon external port: {self.axon.external_port}")
        self.check_endpoint_connection()
        self.check_network_config()

    async def __aenter__(self):
        await self.async_setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.async_teardown()

    async def async_setup(self):
        # Perform any asynchronous setup here
        pass

    async def async_teardown(self):
        # Perform any asynchronous cleanup here
        pass

    def check_endpoint_connection(self):
        bt.logging.info("Checking endpoint connections")
        try:
            response = requests.get(self.get_work_url, timeout=5)
            bt.logging.info(f"Get work endpoint status: {response.status_code}")
        except requests.RequestException as e:
            bt.logging.error(f"Failed to connect to get work endpoint: {e}")
        try:
            response = requests.get(self.submit_work_url, timeout=5)
            bt.logging.info(f"Submit work endpoint status: {response.status_code}")
        except requests.RequestException as e:
            bt.logging.error(f"Failed to connect to submit work endpoint: {e}")

    def check_network_config(self):
        bt.logging.info("Checking network configuration")
        bt.logging.info(f"Subtensor chain endpoint: {self.subtensor.chain_endpoint}")
        bt.logging.info(f"Subtensor network: {self.subtensor.network}")
        bt.logging.info(f"Validator IP: {self.axon.external_ip}")
        bt.logging.info(f"Validator port: {self.axon.external_port}")
        for uid in self.metagraph.uids:
            bt.logging.info(f"Miner {uid} - IP: {self.metagraph.axons[uid].ip}, Port: {self.metagraph.axons[uid].port}")

    async def query_endpoint(self):
        detailed_log(f"Querying endpoint: {self.get_work_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.get_work_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        detailed_log(f"Received data from endpoint: {data}")
                        data['request_id'] = data.get('request_id', 'default_request_id')
                        data['timestamp'] = data.get('timestamp', str(int(time.time())))
                        return data
                    else:
                        detailed_log(f"Failed to query endpoint: {response.status}")
                        return None
        except aiohttp.ClientError as e:
            detailed_log(f"Error querying endpoint: {str(e)}")
            return None

    async def send_work_to_miners(self, work_data):
        detailed_log(f"Sending work to miners: Request ID: {work_data.get('request_id', 'N/A')}")

        miner_responses = []
        for uid in self.metagraph.uids:
            detailed_log(f"Sending work to miner {uid}")
            detailed_log(f"Miner {uid} axon details: {self.metagraph.axons[uid]}")
            try:
                detailed_log(f"nonce_range_start value: {work_data.get('nonce_range_start', 0)}")
                synapse = WorkData.create(
                    work_data={
                        'block': work_data.get('block', ''),
                        'target': work_data.get('target', ''),
                        'nonce_range_start': work_data.get('nonce_range_start', 0),
                        'nonce_range_end': work_data.get('nonce_range_end', 1000000),
                    },
                    request_id=work_data.get('request_id', 'default_request_id'),
                    timestamp=work_data.get('timestamp', str(int(time.time()))),
                    validator_hotkey=self.wallet.hotkey.ss58_address
                )
                detailed_log(f"Created WorkData synapse: {synapse}")
                response = await self.dendrite(
                    axons=[self.metagraph.axons[uid]],
                    synapse=synapse,
                    deserialize=True,
                    timeout=10
                )
                detailed_log(f"Raw response from dendrite: {response}")
                if response and response[0] is not None:
                    detailed_log(f"Response type: {type(response[0])}")
                    detailed_log(f"Response attributes: {dir(response[0])}")
                    if isinstance(response[0], dict):
                        miner_response = response[0]
                        if 'block_hash' in miner_response and 'nonce' in miner_response:
                            miner_response_with_uid = {'uid': uid, 'response': miner_response}
                            detailed_log(f"Received response from miner {uid}: {miner_response_with_uid}")
                            miner_responses.append(miner_response_with_uid)
                        else:
                            detailed_log(f"Miner {uid} returned incomplete response: {miner_response}")
                    elif hasattr(response[0], 'miner_response'):
                        miner_response = response[0].miner_response
                        if miner_response is not None:
                            miner_response_with_uid = {'uid': uid, 'response': miner_response}
                            detailed_log(f"Received response from miner {uid}: {miner_response_with_uid}")
                            miner_responses.append(miner_response_with_uid)
                        else:
                            detailed_log(f"Miner {uid} returned None for miner_response")
                    else:
                        detailed_log(f"Unexpected response format from miner {uid}: {response[0]}")
                else:
                    detailed_log(f"No valid response received from miner {uid}")
            except Exception as e:
                detailed_log(f"Error communicating with miner {uid}: {str(e)}")
                detailed_log(f"Exception type: {type(e)}")
                detailed_log(f"Exception attributes: {dir(e)}")

        detailed_log(f"Finished sending work to all miners. Received {len(miner_responses)} valid responses.")
        return miner_responses

    async def submit_work(self, work):
        detailed_log(f"Submitting work to mining pool: {work}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.submit_work_url, json=work) as response:
                    if response.status == 200:
                        result = await response.json()
                        detailed_log(f"Work submission successful: {result}")
                        return result
                    else:
                        detailed_log(f"Work submission failed: {response.status}")
                        return None
        except aiohttp.ClientError as e:
            detailed_log(f"Error submitting work: {str(e)}")
            return None

    async def forward(self):
        detailed_log("Starting forward pass")
        work_data = await self.query_endpoint()
        if work_data:
            miner_responses = await self.send_work_to_miners(work_data)
            if miner_responses:
                best_response = max(miner_responses, key=lambda x: x['response']['nonce'])
                result = await self.submit_work(best_response['response'])
                if result:
                    detailed_log(f"Forward pass completed successfully. Result: {result}")
                else:
                    detailed_log("Forward pass completed, but work submission failed")
            else:
                detailed_log("Forward pass completed, but no valid responses received from miners")
        else:
            detailed_log("Forward pass failed due to inability to query endpoint")
        detailed_log("Forward pass finished")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args, unknown = parser.parse_known_args()

    if args.debug:
        bt.logging.set_trace(True)
        bt.logging.set_debug(True)

    async with Validator() as validator:
        while True:
            bt.logging.info(f"Validator running... {time.time()}")
            await validator.forward()
            await asyncio.sleep(5)

# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    asyncio.run(main())
