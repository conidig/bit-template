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
import bittensor as bt

from template.protocol import WorkData
from template.validator.reward import get_rewards
from template.utils.uids import get_random_uids


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

    # Get random UIDs for miners to query
    miner_uids = get_random_uids(self, k=self.config.neuron.sample_size)

    # The dendrite client queries the network.
    responses = await self.dendrite(
        # Send the query to selected miner axons in the network.
        axons=[self.metagraph.axons[uid] for uid in miner_uids],
        # Construct a WorkData synapse with the actual work data.
        synapse=WorkData(work_data=work_data, request_id=request_id, timestamp=timestamp, validator_hotkey=validator_hotkey),
        # All responses have the deserialize function called on them before returning.
        deserialize=True,
    )

    # Log the results for monitoring purposes.
    bt.logging.info(f"Received responses: {responses}")

    # Adjust the scores based on responses from miners.
    rewards = get_rewards(self, query=work_data, responses=responses)

    bt.logging.info(f"Scored responses: {rewards}")
    # Update the scores based on the rewards.
    self.update_scores(rewards, miner_uids)

    # Send work to miners
    await self.send_work_to_miners(work_data, request_id, timestamp, validator_hotkey)

    time.sleep(5)
