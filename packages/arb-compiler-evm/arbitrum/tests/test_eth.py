# Copyright 2019-2020, Offchain Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import eth_utils
from pyevmasm import assemble_hex
from unittest import TestCase

from arbitrum import run_vm_once, value
from arbitrum.evm.contract import create_evm_vm
from arbitrum.evm.contract_abi import ContractABI, create_output_handler
from arbitrum import messagestack
from arbitrum.evm.log import EVMStop, EVMRevert, EVMReturn, EVMInvalidSequence
from arbitrum.evm import contract_templates


def make_msg_val(message):
    return [0, 0, message]


def run_until_block(vm, test):
    while True:
        try:
            # print(vm.pc, vm.pc.path)
            run = run_vm_once(vm)
            if not run:
                break
        except Exception as err:
            test.fail("VM run hit error {}".format(err))
        if vm.halted:
            test.fail("VM unintentionally halted")


def make_contract(evm_code, return_type):
    return ContractABI(
        {
            "address": "0x895521964D724c8362A36608AAf09A3D7d0A0445",
            "abi": [
                {
                    "constant": False,
                    "inputs": [],
                    "name": "testMethod",
                    "outputs": [{"name": "", "type": return_type}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                }
            ],
            "name": "TestContract",
            "code": assemble_hex(evm_code),
            "storage": {},
        }
    )


address_string = "0x2c1b4360234d8e65a9e162ef82d70bee71324512"
address = eth_utils.to_int(hexstr=address_string)

dest_address_string = "0x895521964D724c8362A36608AAf09A3D7d0A0445"
dest_address = eth_utils.to_int(hexstr=dest_address_string)


class TestEVM(TestCase):
    _multiprocess_can_split_ = True

    def test_eth(self):
        contract_a = make_contract("", "uint256")
        vm = create_evm_vm([contract_a], False, False)

        arbsys = contract_templates.get_arbsys()
        arbsys_abi = ContractABI(arbsys)

        arbinfo = contract_templates.get_info_contract()
        arbinfo_abi = ContractABI(arbinfo)
        output_handler = create_output_handler([contract_a, arbinfo_abi])
        inbox = value.Tuple([])
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [1, 2345, value.Tuple([address, 100000])]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [4, address, arbinfo_abi.call_getBalance(address_string)]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            0,
                            address,
                            arbsys_abi.withdrawEth(0, 0, dest_address_string, 150000),
                        ]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            0,
                            address,
                            arbsys_abi.withdrawEth(1, 0, dest_address_string, 50000),
                        ]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [4, address, arbinfo_abi.call_getBalance(address_string)]
                    )  # type  # sender
                )
            ),
        )
        vm.env.messages = inbox
        run_until_block(vm, self)
        self.assertEqual(len(vm.logs), 5)
        parsed_out0 = output_handler(vm.logs[0])
        parsed_out1 = output_handler(vm.logs[1])
        parsed_out2 = output_handler(vm.logs[2])
        parsed_out3 = output_handler(vm.logs[3])
        parsed_out4 = output_handler(vm.logs[4])
        self.assertIsInstance(parsed_out0, EVMStop)
        self.assertIsInstance(parsed_out1, EVMReturn)
        self.assertIsInstance(parsed_out2, EVMRevert)
        self.assertIsInstance(parsed_out3, EVMStop)
        self.assertIsInstance(parsed_out4, EVMReturn)

        self.assertEqual(parsed_out1.output_values[0], 100000)
        self.assertEqual(parsed_out4.output_values[0], 50000)

        self.assertEqual(len(vm.sent_messages), 1)
        self.assertEqual(
            vm.sent_messages[0],
            value.Tuple([1, address, value.Tuple([dest_address, 50000])]),
        )

    def test_erc20(self):
        contract_a = make_contract("", "uint256")
        vm = create_evm_vm([contract_a], False, False)

        output_handler = create_output_handler([contract_a])

        erc20 = contract_templates.get_erc20_contract()
        erc20["address"] = "0xfff6baf0b45129dc8d4cd67ddc28a78d8c599faf"
        erc20_abi = ContractABI(erc20)

        inbox = value.Tuple([])
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [2, 2345, value.Tuple([erc20_abi.address, address, 100000])]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            0,
                            address,
                            erc20_abi.withdraw(0, 0, dest_address_string, 150000),
                        ]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            0,
                            address,
                            erc20_abi.withdraw(1, 0, dest_address_string, 50000),
                        ]
                    )  # type  # sender
                )
            ),
        )
        vm.env.messages = inbox
        run_until_block(vm, self)
        self.assertEqual(len(vm.logs), 3)
        parsed_out0 = output_handler(vm.logs[0])
        parsed_out1 = output_handler(vm.logs[1])
        parsed_out2 = output_handler(vm.logs[2])
        self.assertIsInstance(parsed_out0, EVMStop)
        self.assertIsInstance(parsed_out1, EVMRevert)
        self.assertIsInstance(parsed_out2, EVMStop)

        self.assertEqual(len(vm.sent_messages), 1)
        self.assertEqual(
            vm.sent_messages[0],
            value.Tuple(
                [2, address, value.Tuple([erc20_abi.address, dest_address, 50000])]
            ),
        )

    def test_erc721(self):
        contract_a = make_contract("", "uint256")
        vm = create_evm_vm([contract_a], False, False)
        output_handler = create_output_handler([contract_a])

        erc721 = contract_templates.get_erc721_contract()
        erc721["address"] = "0xfff6baf0b45129dc8d4cd67ddc28a78d8c599faf"
        erc721_abi = ContractABI(erc721)
        inbox = value.Tuple([])
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [3, 2345, value.Tuple([erc721_abi.address, address, 100000])]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [3, 2345, value.Tuple([erc721_abi.address, address, 150000])]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [4, address, erc721_abi.call_tokensOfOwner(address_string)]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            0,
                            address,
                            erc721_abi.withdraw(0, 0, dest_address_string, 50000),
                        ]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            0,
                            address,
                            erc721_abi.withdraw(1, 0, dest_address_string, 100000),
                        ]
                    )  # type  # sender
                )
            ),
        )
        vm.env.messages = inbox
        run_until_block(vm, self)
        self.assertEqual(len(vm.logs), 5)
        parsed_out0 = output_handler(vm.logs[0])
        parsed_out1 = output_handler(vm.logs[1])
        parsed_out2 = output_handler(vm.logs[2])
        parsed_out3 = output_handler(vm.logs[3])
        parsed_out4 = output_handler(vm.logs[4])
        self.assertIsInstance(parsed_out0, EVMStop)
        self.assertIsInstance(parsed_out1, EVMStop)
        self.assertIsInstance(parsed_out2, EVMReturn)
        self.assertIsInstance(parsed_out3, EVMRevert)
        self.assertIsInstance(parsed_out4, EVMStop)

        out = parsed_out2.output_values
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], (100000, 150000))

        self.assertEqual(len(vm.sent_messages), 1)
        self.assertEqual(
            vm.sent_messages[0],
            value.Tuple(
                [3, address, value.Tuple([erc721_abi.address, dest_address, 100000])]
            ),
        )

    def test_seq(self):
        contract_a = make_contract("", "uint256")
        vm = create_evm_vm([contract_a], False, False)

        arbsys = contract_templates.get_arbsys()
        arbsys_abi = ContractABI(arbsys)

        output_handler = create_output_handler([contract_a])
        inbox = value.Tuple([])
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [1, 2345, value.Tuple([address, 100000])]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            4,
                            address,
                            arbsys_abi.call_getTransactionCount(address_string),
                        ]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            0,
                            address,
                            arbsys_abi.withdrawEth(0, 0, dest_address_string, 50000),
                        ]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            4,
                            address,
                            arbsys_abi.call_getTransactionCount(address_string),
                        ]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            0,
                            address,
                            arbsys_abi.withdrawEth(5, 0, dest_address_string, 50000),
                        ]
                    )  # type  # sender
                )
            ),
        )
        inbox = messagestack.addMessage(
            inbox,
            value.Tuple(
                make_msg_val(
                    value.Tuple(
                        [
                            0,
                            address,
                            arbsys_abi.withdrawEth(1, 0, dest_address_string, 50000),
                        ]
                    )  # type  # sender
                )
            ),
        )
        vm.env.messages = inbox
        run_until_block(vm, self)
        self.assertEqual(len(vm.logs), 6)
        parsed_out0 = output_handler(vm.logs[0])
        parsed_out1 = output_handler(vm.logs[1])
        parsed_out2 = output_handler(vm.logs[2])
        parsed_out3 = output_handler(vm.logs[3])
        parsed_out4 = output_handler(vm.logs[4])
        parsed_out5 = output_handler(vm.logs[5])
        self.assertIsInstance(parsed_out0, EVMStop)
        self.assertIsInstance(parsed_out1, EVMReturn)
        self.assertIsInstance(parsed_out2, EVMStop)
        self.assertIsInstance(parsed_out3, EVMReturn)
        self.assertIsInstance(parsed_out4, EVMInvalidSequence)
        self.assertIsInstance(parsed_out5, EVMStop)

        self.assertEqual(parsed_out1.output_values[0], 0)
        self.assertEqual(parsed_out3.output_values[0], 1)

        self.assertEqual(len(vm.sent_messages), 2)
        self.assertEqual(
            vm.sent_messages[0],
            value.Tuple([1, address, value.Tuple([dest_address, 50000])]),
        )
        self.assertEqual(
            vm.sent_messages[1],
            value.Tuple([1, address, value.Tuple([dest_address, 50000])]),
        )
