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
import numpy as np
from typing import List, Dict
import bittensor as bt


def reward(query: Dict, response: Dict) -> float:
    """
    Reward the miner response to the work request. This method returns a reward
    value for the miner, which is used to update the miner's score.

    Args:
    - query (Dict): The work data sent to the miner.
    - response (Dict): The response from the miner.

    Returns:
    - float: The reward value for the miner.
    """
    bt.logging.info(
        f"In rewards, query: {query}, response: {response}"
    )
    # Check if either query or response is None
    if query is None or response is None:
        bt.logging.warning("Query or response is None")
        return 0.0

    # Check if both query and response have 'work_data' field
    if 'work_data' not in query or 'work_data' not in response:
        bt.logging.warning("Missing 'work_data' field in query or response")
        return 0.0

    # Compare the 'work_data' field
    if query['work_data'] == response['work_data']:
        return 1.0
    return 0.0


def get_rewards(
    self,
    query: Dict,
    responses: List[Dict],
) -> np.ndarray:
    """
    Returns an array of rewards for the given query and responses.

    Args:
    - query (Dict): The work data sent to the miners.
    - responses (List[Dict]): A list of responses from the miners.

    Returns:
    - np.ndarray: An array of rewards for the given query and responses.
    """
    # Get all the reward results by iteratively calling your reward() function.

    return np.array([reward(query, response) for response in responses])
