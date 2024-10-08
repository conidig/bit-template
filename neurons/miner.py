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
import typing
import bittensor as bt
import requests
import hashlib
import logging

# Bittensor Miner Template:
import template

# import base miner class which takes care of most of the boilerplate
from template.base.miner import BaseMinerNeuron


class Miner(BaseMinerNeuron):
    """
    Your miner neuron class. You should use this class to define your miner's behavior. In particular, you should replace the forward function with your own logic. You may also want to override the blacklist and priority functions according to your needs.

    This class inherits from the BaseMinerNeuron class, which in turn inherits from BaseNeuron. The BaseNeuron class takes care of routine tasks such as setting up wallet, subtensor, metagraph, logging directory, parsing config, etc. You can override any of the methods in BaseNeuron if you need to customize the behavior.

    This class provides reasonable default behavior for a miner such as blacklisting unrecognized hotkeys, prioritizing requests based on stake, and forwarding requests to the forward function. If you need to define custom
    """

    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.submit_url = 'http://71.158.89.73:4437/submit_work'

    @staticmethod
    def double_sha256(block_header):
        return hashlib.sha256(hashlib.sha256(block_header.encode('utf-8')).digest()).hexdigest()

    @staticmethod
    def bits_to_target(bits):
        exponent = (bits >> 24) & 0xff
        mantissa = bits & 0xffffff
        target = mantissa * (1 << (8 * (exponent - 3)))
        return target

    async def forward(self, synapse: template.protocol.WorkData) -> template.protocol.WorkData:
        self.logger.info(f"Received work data: {synapse.work_data}")
        block = synapse.work_data.get('block')
        target = synapse.work_data.get('target')
        nonce_range_start = synapse.work_data.get('nonce_range_start')
        nonce_range_end = synapse.work_data.get('nonce_range_end')

        if not all([block, target, nonce_range_start, nonce_range_end]):
            missing_fields = []
            if not block:
                missing_fields.append('block')
            if not target:
                missing_fields.append('target')
            if not nonce_range_start:
                missing_fields.append('nonce_range_start')
            if not nonce_range_end:
                missing_fields.append('nonce_range_end')

            self.logger.error(f"Invalid work data received. Missing fields: {', '.join(missing_fields)}")
            return synapse

        self.logger.info(f"Starting mining process for block: {block[:10]}...")
        self.logger.info(f"Target: {target}")
        self.logger.info(f"Assigned nonce range: {nonce_range_start} to {nonce_range_end}")

        hashes_computed = 0
        start_time = time.time()

        for nonce in range(nonce_range_start, nonce_range_end):
            block_header = block + str(nonce)
            block_hash = self.double_sha256(block_header)
            hashes_computed += 1

            if int(block_hash, 16) < int(target, 16):
                end_time = time.time()
                duration = end_time - start_time
                hash_rate = hashes_computed / duration if duration > 0 else 0
                self.logger.info(f"Found valid hash: {block_hash} with nonce: {nonce}")
                self.logger.info(f"Hashing took {duration:.2f} seconds")
                self.logger.info(f"Hash rate: {hash_rate:.2f} hashes/second")
                synapse.miner_response = {'block_hash': block_hash, 'nonce': nonce}
                break

            if hashes_computed % 1000 == 0:
                self.logger.info(f"Computed {hashes_computed} hashes...")

        if not synapse.miner_response:
            end_time = time.time()
            duration = end_time - start_time
            hash_rate = hashes_computed / duration if duration > 0 else 0
            self.logger.info("No valid hash found in given range")
            self.logger.info(f"Hashing took {duration:.2f} seconds")
            self.logger.info(f"Hash rate: {hash_rate:.2f} hashes/second")

        self.logger.info(f"Sending response: {synapse.miner_response}")
        return synapse

    async def blacklist(
        self, synapse: template.protocol.WorkData
    ) -> typing.Tuple[bool, str]:
        """
        Determines whether an incoming request should be blacklisted and thus ignored. Your implementation should
        define the logic for blacklisting requests based on your needs and desired security parameters.

        Blacklist runs before the synapse data has been deserialized (i.e. before synapse.data is available).
        The synapse is instead contracted via the headers of the request. It is important to blacklist
        requests before they are deserialized to avoid wasting resources on requests that will be ignored.

        Args:
            synapse (template.protocol.WorkData): A synapse object constructed from the headers of the incoming request.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether the synapse's hotkey is blacklisted,
                            and a string providing the reason for the decision.

        This function is a security measure to prevent resource wastage on undesired requests. It should be enhanced
        to include checks against the metagraph for entity registration, validator status, and sufficient stake
        before deserialization of synapse data to minimize processing overhead.

        Example blacklist logic:
        - Reject if the hotkey is not a registered entity within the metagraph.
        - Consider blacklisting entities that are not validators or have insufficient stake.

        In practice it would be wise to blacklist requests from entities that are not validators, or do not have
        enough stake. This can be checked via metagraph.S and metagraph.validator_permit. You can always attain
        the uid of the sender via a metagraph.hotkeys.index( synapse.dendrite.hotkey ) call.

        Otherwise, allow the request to be processed further.
        """

        if synapse.dendrite is None or synapse.dendrite.hotkey is None:
            bt.logging.warning(
                "Received a request without a dendrite or hotkey."
            )
            return True, "Missing dendrite or hotkey"

        # TODO(developer): Define how miners should blacklist requests.
        uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        if (
            not self.config.blacklist.allow_non_registered
            and synapse.dendrite.hotkey not in self.metagraph.hotkeys
        ):
            # Ignore requests from un-registered entities.
            bt.logging.trace(
                f"Blacklisting un-registered hotkey {synapse.dendrite.hotkey}"
            )
            return True, "Unrecognized hotkey"

        if self.config.blacklist.force_validator_permit:
            # If the config is set to force validator permit, then we should only allow requests from validators.
            if not self.metagraph.validator_permit[uid]:
                bt.logging.warning(
                    f"Blacklisting a request from non-validator hotkey {synapse.dendrite.hotkey}"
                )
                return True, "Non-validator hotkey"

        bt.logging.trace(
            f"Not Blacklisting recognized hotkey {synapse.dendrite.hotkey}"
        )
        return False, "Hotkey recognized!"

    async def priority(self, synapse: template.protocol.WorkData) -> float:
        """
        The priority function determines the order in which requests are handled. More valuable or higher-priority
        requests are processed before others. You should design your own priority mechanism with care.

        This implementation assigns priority to incoming requests based on the calling entity's stake in the metagraph.

        Args:
            synapse (template.protocol.WorkData): The synapse object that contains metadata about the incoming request.

        Returns:
            float: A priority score derived from the stake of the calling entity.

        Miners may receive messages from multiple entities at once. This function determines which request should be
        processed first. Higher values indicate that the request should be processed first. Lower values indicate
        that the request should be processed later.

        Example priority logic:
        - A higher stake results in a higher priority value.
        """
        if synapse.dendrite is None or synapse.dendrite.hotkey is None:
            bt.logging.warning(
                "Received a request without a dendrite or hotkey."
            )
            return 0.0

        # TODO(developer): Define how miners should prioritize requests.
        caller_uid = self.metagraph.hotkeys.index(
            synapse.dendrite.hotkey
        )  # Get the caller index.
        priority = float(
            self.metagraph.S[caller_uid]
        )  # Return the stake as the priority.
        bt.logging.trace(
            f"Prioritizing {synapse.dendrite.hotkey} with value: {priority}"
        )
        return priority


# This is the main function, which runs the miner.
if __name__ == "__main__":
    with Miner() as miner:
        while True:
            bt.logging.info(f"Miner running... {time.time()}")
            time.sleep(5)
