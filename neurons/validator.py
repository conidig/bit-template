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

# Bittensor
import bittensor as bt

# Additional imports
import numpy as np  # For handling numpy data types

# Import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron

# Bittensor Validator Template:
from template.validator import forward
from template.protocol import WorkData

# Helper function to convert numpy data types to native types
def convert_to_serializable(obj):
    if isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(element) for element in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    else:
        return obj

class Validator(BaseValidatorNeuron):
    """
    Validator neuron class. This class defines the validator's behavior, particularly the `forward` method.
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
        bt.logging.info(f"Querying endpoint: {self.get_work_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.get_work_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Use default values if 'request_id' or 'timestamp' are missing
                        data['request_id'] = data.get('request_id', 'default_request_id')
                        data['timestamp'] = data.get('timestamp', str(int(time.time())))
                        return data
                    else:
                        bt.logging.error(f"Failed to query endpoint: {response.status}")
                        return None
        except aiohttp.ClientError as e:
            bt.logging.error(f"Error querying endpoint: {str(e)}")
            return None

    async def send_work_to_miners(self, work_data):
        bt.logging.info(f"Sending work to miners: Request ID: {work_data.get('request_id', 'N/A')}")

        miner_responses = []
        total_nonce_range_start = work_data.get('nonce_range_start', 0)
        total_nonce_range_end = work_data.get('nonce_range_end', 1000000)
        total_nonce_range_size = total_nonce_range_end - total_nonce_range_start + 1
        num_miners = len(self.metagraph.uids)
        nonce_range_per_miner = total_nonce_range_size // num_miners if num_miners > 0 else total_nonce_range_size

        for idx, uid in enumerate(self.metagraph.uids):
            bt.logging.info(f"Sending work to miner {uid}")
            bt.logging.info(f"Miner {uid} axon details: {self.metagraph.axons[uid]}")

            # Calculate unique nonce ranges for each miner
            miner_nonce_start = total_nonce_range_start + idx * nonce_range_per_miner
            miner_nonce_end = miner_nonce_start + nonce_range_per_miner - 1

            # Ensure the last miner covers any remaining nonces
            if idx == num_miners - 1:
                miner_nonce_end = total_nonce_range_end

            bt.logging.info(f"Assigned nonce range {miner_nonce_start} to {miner_nonce_end} for miner {uid}")

            try:
                synapse = WorkData(
                    work_data={
                        'block': work_data.get('block', ''),
                        'target': work_data.get('target', ''),
                        'nonce_range_start': miner_nonce_start,
                        'nonce_range_end': miner_nonce_end,
                        'transactions': work_data.get('transactions', [])
                    },
                    request_id=work_data.get('request_id', 'default_request_id'),
                    timestamp=work_data.get('timestamp', str(int(time.time()))),
                    validator_hotkey=self.wallet.hotkey.ss58_address
                )
                bt.logging.info(f"Created synapse")
                response = await self.dendrite(
                    axons=[self.metagraph.axons[uid]],
                    synapse=synapse,
                    deserialize=True,
                    timeout=60  # Adjust timeout as needed
                )
                bt.logging.info(f"Raw response from dendrite: {response}")
                if response and response[0] is not None:
                    # Access the correct keys from the response
                    miner_response = {
                        'uid': int(uid),  # Convert uid to int
                        'block_hash': response[0]['block_hash'],
                        'nonce': int(response[0]['nonce'])  # Convert nonce to int
                    }
                    bt.logging.info(f"Received response from miner {uid}: {miner_response}")
                    miner_responses.append(miner_response)
                else:
                    bt.logging.warning(f"No valid response received from miner {uid}")
            except Exception as e:
                bt.logging.error(f"Error communicating with miner {uid}: {str(e)}")
                bt.logging.error(f"Exception details: {type(e).__name__}, {str(e)}")

        bt.logging.info(f"Finished sending work to all miners. Received {len(miner_responses)} valid responses.")
        return miner_responses

    async def submit_work(self, best_response):
        bt.logging.info(f"Submitting work to: {self.submit_work_url}")
        try:
            # Convert best_response to serializable types
            best_response_serializable = convert_to_serializable(best_response)
            async with aiohttp.ClientSession() as session:
                async with session.post(self.submit_work_url, json=best_response_serializable) as response:
                    if response.status == 200:
                        bt.logging.info("Work submitted successfully")
                        return True
                    else:
                        bt.logging.error(f"Failed to submit work. Status: {response.status}")
                        return False
        except Exception as e:
            bt.logging.error(f"Error submitting work: {e}")
            return False

    async def forward(self):
        bt.logging.info("Starting forward pass")
        try:
            bt.logging.info("Attempting to query endpoint")
            work_data = await self.query_endpoint()
            if work_data:
                bt.logging.info("Successfully received work data. Attempting to send work to miners")
                miner_responses = await self.send_work_to_miners(work_data)
                bt.logging.info(f"Received miner responses: {miner_responses}")
                if miner_responses:
                    # Select the best response based on the lowest block hash value
                    best_response = min(miner_responses, key=lambda x: int(x['block_hash'], 16))
                    bt.logging.info(f"Best response: {best_response}")
                    submit_result = await self.submit_work(best_response)
                    bt.logging.info(f"Work submission result: {submit_result}")
                else:
                    bt.logging.warning("No valid responses from miners")
            else:
                bt.logging.error("Failed to get work from endpoint")
        except Exception as e:
            bt.logging.error(f"Error in forward pass: {str(e)}")
            bt.logging.error(f"Exception details: {type(e).__name__}, {str(e)}")

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
