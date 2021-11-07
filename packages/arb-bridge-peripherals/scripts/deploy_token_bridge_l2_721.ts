import { ethers } from 'hardhat'
import { deploy1820Registry } from './utils'
import { writeFileSync } from 'fs'
import deployments from '../deployment.json'

const main = async () => {
  const accounts = await ethers.getSigners()
  const StandardArbERC721 = await ethers.getContractFactory('StandardArbERC721')

  const standardArbERC721Logic = await StandardArbERC721.deploy()
  await standardArbERC721Logic.deployed()
  console.log(`erc721 logic at ${standardArbERC721Logic.address}`)

  // const ProxyAdmin = await ethers.getContractFactory('ProxyAdmin')
  // const proxyAdmin = await ProxyAdmin.deploy()
  // await proxyAdmin.deployed()
  // console.log("Admin proxy deployed to", proxyAdmin.address)

  const UpgradeableBeacon = await ethers.getContractFactory('UpgradeableBeacon')

  const standardArbERC721Proxy = await UpgradeableBeacon.deploy(
    standardArbERC721Logic.address
  )
  await standardArbERC721Proxy.deployed()
  console.log(`erc721 proxy at ${standardArbERC721Proxy.address}`)

  const contracts = JSON.stringify({
    ...deployments,
    // standardArbERC721: standardArbERC721Logic.address,
    standardArbERC721: standardArbERC721Proxy.address,
    l2ChainId: ethers.BigNumber.from(
      ethers.provider.network.chainId
    ).toHexString(),
  })

  const path = './deployment.json'
  console.log(`Writing to JSON at ${path}`)

  // TODO: should append/check if previous entries
  writeFileSync(path, contracts)

  console.log('Almost done')
  await deploy1820Registry(accounts[0])
  console.log('Done')
}

main()
  .then(() => process.exit(0))
  .catch(error => {
    console.error(error)
    process.exit(1)
  })
