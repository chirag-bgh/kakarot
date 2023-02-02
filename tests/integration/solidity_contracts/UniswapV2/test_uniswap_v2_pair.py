import pytest

from tests.integration.helpers.constants import ZERO_ADDRESS
from tests.integration.helpers.helpers import expand_to_18_decimals
from tests.utils.errors import kakarot_error

MINIMUM_LIQUIDITY = 10**3


@pytest.mark.asyncio
@pytest.mark.UniswapV2Pair
@pytest.mark.usefixtures("starknet_snapshot")
class TestUniswapV2Pair:
    class TestMint:
        async def test_should_mint(self, pair, owner):
            pair, token_0, token_1 = pair
            token_0_amount = expand_to_18_decimals(1)
            token_1_amount = expand_to_18_decimals(4)
            await token_0.transfer(
                to=pair.evm_contract_address,
                value=token_0_amount,
                caller_address=owner.starknet_address,
            )
            await token_1.transfer(
                to=pair.evm_contract_address,
                value=token_1_amount,
                caller_address=owner.starknet_address,
            )

            expected_liquidity = expand_to_18_decimals(2)
            await pair.mint(owner.address, caller_address=owner.starknet_address)
            assert pair.events.Transfer == [
                {"from": ZERO_ADDRESS, "to": ZERO_ADDRESS, "value": MINIMUM_LIQUIDITY},
                {
                    "from": ZERO_ADDRESS,
                    "to": owner.address,
                    "value": expected_liquidity - MINIMUM_LIQUIDITY,
                },
            ]
            assert pair.events.Sync == [
                {
                    "reserve0": token_0_amount,
                    "reserve1": token_1_amount,
                }
            ]
            assert pair.events.Mint == [
                {
                    "sender": owner.address,
                    "amount0": token_0_amount,
                    "amount1": token_1_amount,
                }
            ]

            assert await pair.totalSupply() == expected_liquidity
            assert (
                await pair.balanceOf(owner.address)
                == expected_liquidity - MINIMUM_LIQUIDITY
            )
            assert await token_0.balanceOf(pair.evm_contract_address) == token_0_amount
            assert await token_1.balanceOf(pair.evm_contract_address) == token_1_amount
            reserves = await pair.getReserves()
            assert reserves[0] == token_0_amount
            assert reserves[1] == token_1_amount

    class TestAddLiquidity:
        @pytest.mark.parametrize(
            "swap_amount, token_0_amount, token_1_amount, expected_output_amount",
            [
                [1, 5, 10, 1662497915624478906],
                [1, 10, 5, 453305446940074565],
                [2, 5, 10, 2851015155847869602],
                [2, 10, 5, 831248957812239453],
                [1, 10, 10, 906610893880149131],
                [1, 100, 100, 987158034397061298],
                [1, 1000, 1000, 996006981039903216],
                [1, 5, 10, 997000000000000000],
                [1, 10, 5, 997000000000000000],
                [1, 5, 5, 997000000000000000],
                [1003009027081243732, 5, 5, 1],
            ],
        )
        async def test_should_add_liquidity(
            self,
            pair,
            owner,
            swap_amount,
            token_0_amount,
            token_1_amount,
            expected_output_amount,
        ):
            pair, token_0, token_1 = pair
            await token_0.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_0_amount),
                caller_address=owner.starknet_address,
            )
            await token_1.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_1_amount),
                caller_address=owner.starknet_address,
            )
            await pair.mint(owner.address, caller_address=owner.starknet_address)

            await token_0.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(swap_amount),
                caller_address=owner.starknet_address,
            )
            with kakarot_error("UniswapV2: K"):
                pair.swap(
                    amount0Out=0,
                    amount1Out=expected_output_amount + 1,
                    to=owner.address,
                    data=b"",
                    caller_address=owner.starknet_address,
                )
            await pair.swap(
                amount0Out=0,
                amount1Out=expected_output_amount,
                to=owner.address,
                data=b"",
                caller_address=owner.starknet_address,
            )

    class TestSwap:
        async def test_should_swap_token_0(self, pair, owner):
            pair, token_0, token_1 = pair
            token_0_amount = expand_to_18_decimals(5)
            token_1_amount = expand_to_18_decimals(10)
            await token_0.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_0_amount),
                caller_address=owner.starknet_address,
            )
            await token_1.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_1_amount),
                caller_address=owner.starknet_address,
            )
            await pair.mint(owner.address, caller_address=owner.starknet_address)

            swap_amount = expand_to_18_decimals(1)
            expected_output_amount = 1662497915624478906
            await token_0.transfer(
                pair.evm_contract_address,
                swap_amount,
                caller_address=owner.starknet_address,
            )

            await pair.swap(
                amount0Out=0,
                amount1Out=expected_output_amount,
                to=owner.address,
                data=b"",
                caller_address=owner.starknet_address,
            )
            assert pair.events.Transfer == [
                {
                    "from": pair.evm_contract_address,
                    "to": owner.address,
                    "value": expected_output_amount,
                }
            ]
            assert pair.events.Sync == [
                {
                    "reserve0": token_0_amount + swap_amount,
                    "reserve1": token_1_amount - expected_output_amount,
                }
            ]
            assert pair.events.Swap == [
                {
                    "sender": owner.address,
                    "amount0In": swap_amount,
                    "amount1In": 0,
                    "amount0Out": 0,
                    "amount1Out": expected_output_amount,
                    "to": owner.address,
                }
            ]

            reserves = await pair.getReserves()
            assert reserves[0] == token_0_amount + swap_amount
            assert reserves[1] == token_1_amount - expected_output_amount
            assert (
                await token_0.balanceOf(pair.evm_contract_address)
                == token_0_amount + swap_amount
            )
            assert (
                await token_1.balanceOf(pair.evm_contract_address)
                == token_1_amount - expected_output_amount
            )
            total_supply_token0 = await token_0.totalSupply()
            total_supply_token1 = await token_1.totalSupply()
            assert (
                await token_0.balanceOf(owner.address)
                == total_supply_token0 - token_0_amount - swap_amount
            )
            assert (
                await token_1.balanceOf(owner.address)
                == total_supply_token1 - token_1_amount + expected_output_amount
            )

        async def test_should_swap_token_1(self, pair, owner):
            pair, token_0, token_1 = pair
            token_0_amount = expand_to_18_decimals(5)
            token_1_amount = expand_to_18_decimals(10)
            await token_0.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_0_amount),
                caller_address=owner.starknet_address,
            )
            await token_1.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_1_amount),
                caller_address=owner.starknet_address,
            )
            await pair.mint(owner.address, caller_address=owner.starknet_address)

            swap_amount = expand_to_18_decimals(1)
            expected_output_amount = 453305446940074565
            await token_1.transfer(pair.evm_contract_address, swap_amount)

            await pair.swap(
                expected_output_amount,
                0,
                owner.address,
                "0x",
                caller_address=owner.starknet_address,
            )
            assert pair.events.Transfer == [
                {
                    "from": pair.evm_contract_address,
                    "to": owner.address,
                    "value": expected_output_amount,
                }
            ]

            assert pair.events.Sync == [
                {
                    "reserve0": token_0_amount - expected_output_amount,
                    "reserve1": token_1_amount + swap_amount,
                }
            ]
            assert pair.events.Swap == [
                {
                    "sender": owner.address,
                    "amount0In": 0,
                    "amount1In": swap_amount,
                    "amount0Out": expected_output_amount,
                    "amount1Out": 0,
                    "to": owner.address,
                }
            ]

            reserves = await pair.getReserves()
            assert reserves[0] == token_0_amount - expected_output_amount
            assert reserves[1] == token_1_amount + swap_amount
            assert (
                await token_0.balanceOf(pair.evm_contract_address)
                == token_0_amount - expected_output_amount
            )
            assert (
                await token_1.balanceOf(pair.evm_contract_address)
                == token_1_amount + swap_amount
            )

            total_supply_token0 = await token_0.totalSupply()
            total_supply_token1 = await token_1.totalSupply()
            assert (
                await token_0.balanceOf(owner.address)
                == total_supply_token0 - token_0_amount + expected_output_amount
            )
            assert (
                await token_1.balanceOf(owner.address)
                == total_supply_token1 - token_1_amount - swap_amount
            )

        @pytest.mark.skip("gas_usage is not yet returned by kakarot")
        async def test_should_use_correct_gas(self, starknet, pair, owner, mine_block):
            # TODO: see https://github.com/sayajin-labs/kakarot/issues/428
            pair, token_0, token_1 = pair
            token_0_amount = expand_to_18_decimals(5)
            token_1_amount = expand_to_18_decimals(10)
            await token_0.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_0_amount),
                caller_address=owner.starknet_address,
            )
            await token_1.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_1_amount),
                caller_address=owner.starknet_address,
            )
            await pair.mint(owner.address, caller_address=owner.starknet_address)
            # ensure that setting price{0,1}CumulativeLast for the first time doesn't affect our gas math
            mine_block()
            await pair.sync(caller_address=owner.starknet_address)

            swap_amount = expand_to_18_decimals(1)
            expected_output_amount = 453305446940074565
            await token_1.transfer(
                pair.evm_contract_address,
                swap_amount,
                caller_address=owner.starknet_address,
            )
            mine_block()
            tx = await pair.swap(expected_output_amount, 0, owner.address, b"")
            assert tx.gas_used == 73462

    class TestBurn:
        async def test_should_burn(self, pair, owner):
            pair, token_0, token_1 = pair
            token_0_amount = expand_to_18_decimals(5)
            token_1_amount = expand_to_18_decimals(10)
            await token_0.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_0_amount),
                caller_address=owner.starknet_address,
            )
            await token_1.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_1_amount),
                caller_address=owner.starknet_address,
            )
            await pair.mint(owner.address, caller_address=owner.starknet_address)

            expected_liquidity = expand_to_18_decimals(3)
            await pair.transfer(
                pair.evm_contract_address,
                expected_liquidity - MINIMUM_LIQUIDITY,
                caller_address=owner.starknet_address,
            )

            await pair.burn(owner.address, caller_address=owner.starknet_address)

            assert pair.events.Transfer == [
                {
                    "from": pair.evm_contract_address,
                    "to": ZERO_ADDRESS,
                    "value": expected_liquidity - MINIMUM_LIQUIDITY,
                }
            ]

            assert token_0.events.Transfer == [
                {
                    "from": pair.evm_contract_address,
                    "to": owner.address,
                    "value": token_0_amount - 1000,
                }
            ]
            assert token_1.events.Transfer == [
                {
                    "from": pair.evm_contract_address,
                    "to": owner.address,
                    "value": token_1_amount - 1000,
                }
            ]
            assert pair.events.Sync == [{"reserve0": 1000, "reserver1": 1000}]
            assert pair.events.Burn == [
                {
                    "sender": owner.address,
                    "amount0": token_0_amount - 1000,
                    "amount1": token_1_amount - 1000,
                    "to": owner.address,
                }
            ]

            assert await pair.balanceOf(owner.address) == 0
            assert await pair.totalSupply() == MINIMUM_LIQUIDITY
            assert await token_0.balanceOf(pair.evm_contract_address) == 1000
            assert await token_1.balanceOf(pair.evm_contract_address) == 1000
            total_supply_token0 = await token_0.totalSupply()
            total_supply_token1 = await token_1.totalSupply()
            assert await token_0.balanceOf(owner.address) == total_supply_token0 - 1000
            assert await token_1.balanceOf(owner.address) == total_supply_token1 - 1000

    class TestPriceCumulative:
        async def test_should_correct_prices(self, pair, owner, mine_block):
            pair, token_0, token_1 = pair
            token_0_amount = expand_to_18_decimals(3)
            token_1_amount = expand_to_18_decimals(3)
            await token_0.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_0_amount),
                caller_address=owner.starknet_address,
            )
            await token_1.transfer(
                to=pair.evm_contract_address,
                value=expand_to_18_decimals(token_1_amount),
                caller_address=owner.starknet_address,
            )
            await pair.mint(owner.address, caller_address=owner.starknet_address)

            block_timestamp = (await pair.getReserves())[2]
            mine_block(timestamp=block_timestamp + 1)

            await pair.sync(caller_address=owner.starknet_address)


#     initialPrice = encodePrice(token_0_amount, token_1_amount)
#     expect(await pair.price0CumulativeLast()).to.eq(initialPrice[0])
#     expect(await pair.price1CumulativeLast()).to.eq(initialPrice[1])
#     expect((await pair.getReserves())[2]).to.eq(blockTimestamp + 1)

#     swap_amount = expand_to_18_decimals(3)
#     await token_0.transfer(pair.evm_contract_address, swap_amount)
#     await mineBlock(provider, blockTimestamp + 10)
#     // swap to a new price eagerly instead of syncing
#     await pair.swap(0, expand_to_18_decimals(1), owner.address, "0x", overrides) // make the price nice

#     expect(await pair.price0CumulativeLast()).to.eq(initialPrice[0].mul(10))
#     expect(await pair.price1CumulativeLast()).to.eq(initialPrice[1].mul(10))
#     expect((await pair.getReserves())[2]).to.eq(blockTimestamp + 10)

#     await mineBlock(provider, blockTimestamp + 20)
#     await pair.sync(overrides)

#     newPrice = encodePrice(expand_to_18_decimals(6), expand_to_18_decimals(2))
#     expect(await pair.price0CumulativeLast()).to.eq(
#       initialPrice[0].mul(10).add(newPrice[0].mul(10))
#     )
#     expect(await pair.price1CumulativeLast()).to.eq(
#       initialPrice[1].mul(10).add(newPrice[1].mul(10))
#     )
#     expect((await pair.getReserves())[2]).to.eq(blockTimestamp + 20)
#   })

#   it("feeTo:off", async () => {
#     token_0_amount = expand_to_18_decimals(1000)
#     token_1_amount = expand_to_18_decimals(1000)
#     await addLiquidity(token_0_amount, token_1_amount)

#     swap_amount = expand_to_18_decimals(1)
#     expected_output_amount = bigNumberify("996006981039903216")
#     await token_1.transfer(pair.evm_contract_address, swap_amount)
#     await pair.swap(expected_output_amount, 0, owner.address, "0x", overrides)

#     expected_liquidity = expand_to_18_decimals(1000)
#     await pair.transfer(pair.evm_contract_address, expected_liquidity.sub(MINIMUM_LIQUIDITY))
#     await pair.burn(owner.address, overrides)
#     expect(await pair.totalSupply()).to.eq(MINIMUM_LIQUIDITY)
#   })

#   it("feeTo:on", async () => {
#     await factory.setFeeTo(other.address)

#     token_0_amount = expand_to_18_decimals(1000)
#     token_1_amount = expand_to_18_decimals(1000)
#     await addLiquidity(token_0_amount, token_1_amount)

#     swap_amount = expand_to_18_decimals(1)
#     expected_output_amount = bigNumberify("996006981039903216")
#     await token_1.transfer(pair.evm_contract_address, swap_amount)
#     await pair.swap(expected_output_amount, 0, owner.address, "0x", overrides)

#     expected_liquidity = expand_to_18_decimals(1000)
#     await pair.transfer(pair.evm_contract_address, expected_liquidity.sub(MINIMUM_LIQUIDITY))
#     await pair.burn(owner.address, overrides)
#     expect(await pair.totalSupply()).to.eq(
#       MINIMUM_LIQUIDITY.add("249750499251388")
#     )
#     expect(await pair.balanceOf(other.address)).to.eq("249750499251388")

#     // using 1000 here instead of the symbolic MINIMUM_LIQUIDITY because the amounts only happen to be equal...
#     // ...because the initial liquidity amounts were equal
#     expect(await token_0.balanceOf(pair.evm_contract_address)).to.eq(
#       bigNumberify(1000).add("249501683697445")
#     )
#     expect(await token_1.balanceOf(pair.evm_contract_address)).to.eq(
#       bigNumberify(1000).add("250000187312969")
#     )
#   })
# })