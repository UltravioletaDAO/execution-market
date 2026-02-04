import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";

// Load environment variables
import * as dotenv from "dotenv";
dotenv.config();

const PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY || process.env.PRIVATE_KEY;
if (!PRIVATE_KEY) {
  // Allow hardhat/localhost without key, but fail fast for real networks
  console.warn("WARNING: No DEPLOYER_PRIVATE_KEY or PRIVATE_KEY set. Only hardhat/localhost networks will work.");
}

// Safe accessor for networks that require a real key
const getAccountsConfig = () => {
  if (!PRIVATE_KEY) {
    throw new Error("DEPLOYER_PRIVATE_KEY environment variable is required for non-local networks");
  }
  return [PRIVATE_KEY];
};

// Block explorer API keys
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY || "";
const BASESCAN_API_KEY = process.env.BASESCAN_API_KEY || "";
const SNOWTRACE_API_KEY = process.env.SNOWTRACE_API_KEY || "";
const POLYGONSCAN_API_KEY = process.env.POLYGONSCAN_API_KEY || "";
const OPTIMISM_API_KEY = process.env.OPTIMISM_API_KEY || "";
const ARBISCAN_API_KEY = process.env.ARBISCAN_API_KEY || "";
const CELOSCAN_API_KEY = process.env.CELOSCAN_API_KEY || "";
const BSCSCAN_API_KEY = process.env.BSCSCAN_API_KEY || "";
const SCROLLSCAN_API_KEY = process.env.SCROLLSCAN_API_KEY || "";

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      viaIR: true,
    },
  },
  networks: {
    // Local
    hardhat: {
      chainId: 31337,
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },

    // ============ ETHEREUM ============
    ethereum: {
      url: process.env.ETHEREUM_RPC_URL || "https://eth.llamarpc.com",
      chainId: 1,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
    ethereumSepolia: {
      url: process.env.ETHEREUM_SEPOLIA_RPC_URL || "https://rpc.sepolia.org",
      chainId: 11155111,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },

    // ============ BASE ============
    base: {
      url: process.env.BASE_RPC_URL || "https://mainnet.base.org",
      chainId: 8453,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
    baseSepolia: {
      url: process.env.BASE_SEPOLIA_RPC_URL || "https://sepolia.base.org",
      chainId: 84532,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },

    // ============ AVALANCHE ============
    avalanche: {
      url: process.env.AVALANCHE_RPC_URL || "https://api.avax.network/ext/bc/C/rpc",
      chainId: 43114,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
    avalancheFuji: {
      url: process.env.AVALANCHE_FUJI_RPC_URL || "https://api.avax-test.network/ext/bc/C/rpc",
      chainId: 43113,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },

    // ============ POLYGON ============
    polygon: {
      url: process.env.POLYGON_RPC_URL || "https://polygon-rpc.com",
      chainId: 137,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
    polygonAmoy: {
      url: process.env.POLYGON_AMOY_RPC_URL || "https://rpc-amoy.polygon.technology",
      chainId: 80002,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },

    // ============ OPTIMISM ============
    optimism: {
      url: process.env.OPTIMISM_RPC_URL || "https://mainnet.optimism.io",
      chainId: 10,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
    optimismSepolia: {
      url: process.env.OPTIMISM_SEPOLIA_RPC_URL || "https://sepolia.optimism.io",
      chainId: 11155420,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },

    // ============ ARBITRUM ============
    arbitrum: {
      url: process.env.ARBITRUM_RPC_URL || "https://arb1.arbitrum.io/rpc",
      chainId: 42161,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
    arbitrumSepolia: {
      url: process.env.ARBITRUM_SEPOLIA_RPC_URL || "https://sepolia-rollup.arbitrum.io/rpc",
      chainId: 421614,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },

    // ============ CELO ============
    celo: {
      url: process.env.CELO_RPC_URL || "https://forno.celo.org",
      chainId: 42220,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
    celoAlfajores: {
      url: process.env.CELO_ALFAJORES_RPC_URL || "https://alfajores-forno.celo-testnet.org",
      chainId: 44787,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },

    // ============ BSC ============
    bsc: {
      url: process.env.BSC_RPC_URL || "https://bsc-dataseed.binance.org",
      chainId: 56,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
    bscTestnet: {
      url: process.env.BSC_TESTNET_RPC_URL || "https://data-seed-prebsc-1-s1.binance.org:8545",
      chainId: 97,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },

    // ============ SCROLL ============
    scroll: {
      url: process.env.SCROLL_RPC_URL || "https://rpc.scroll.io",
      chainId: 534352,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
    scrollSepolia: {
      url: process.env.SCROLL_SEPOLIA_RPC_URL || "https://sepolia-rpc.scroll.io",
      chainId: 534351,
      accounts: getAccountsConfig(),
      gasPrice: "auto",
    },
  },
  etherscan: {
    apiKey: {
      // Ethereum
      mainnet: ETHERSCAN_API_KEY,
      sepolia: ETHERSCAN_API_KEY,
      // Base
      base: BASESCAN_API_KEY,
      baseSepolia: BASESCAN_API_KEY,
      // Avalanche
      avalanche: SNOWTRACE_API_KEY,
      avalancheFuji: SNOWTRACE_API_KEY,
      // Polygon
      polygon: POLYGONSCAN_API_KEY,
      polygonAmoy: POLYGONSCAN_API_KEY,
      // Optimism
      optimisticEthereum: OPTIMISM_API_KEY,
      optimismSepolia: OPTIMISM_API_KEY,
      // Arbitrum
      arbitrumOne: ARBISCAN_API_KEY,
      arbitrumSepolia: ARBISCAN_API_KEY,
      // Celo
      celo: CELOSCAN_API_KEY,
      celoAlfajores: CELOSCAN_API_KEY,
      // BSC
      bsc: BSCSCAN_API_KEY,
      bscTestnet: BSCSCAN_API_KEY,
      // Scroll
      scroll: SCROLLSCAN_API_KEY,
      scrollSepolia: SCROLLSCAN_API_KEY,
    },
    customChains: [
      // Base
      {
        network: "base",
        chainId: 8453,
        urls: {
          apiURL: "https://api.basescan.org/api",
          browserURL: "https://basescan.org",
        },
      },
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://api-sepolia.basescan.org/api",
          browserURL: "https://sepolia.basescan.org",
        },
      },
      // Avalanche
      {
        network: "avalanche",
        chainId: 43114,
        urls: {
          apiURL: "https://api.snowtrace.io/api",
          browserURL: "https://snowtrace.io",
        },
      },
      {
        network: "avalancheFuji",
        chainId: 43113,
        urls: {
          apiURL: "https://api-testnet.snowtrace.io/api",
          browserURL: "https://testnet.snowtrace.io",
        },
      },
      // Polygon Amoy
      {
        network: "polygonAmoy",
        chainId: 80002,
        urls: {
          apiURL: "https://api-amoy.polygonscan.com/api",
          browserURL: "https://amoy.polygonscan.com",
        },
      },
      // Optimism Sepolia
      {
        network: "optimismSepolia",
        chainId: 11155420,
        urls: {
          apiURL: "https://api-sepolia-optimistic.etherscan.io/api",
          browserURL: "https://sepolia-optimism.etherscan.io",
        },
      },
      // Arbitrum Sepolia
      {
        network: "arbitrumSepolia",
        chainId: 421614,
        urls: {
          apiURL: "https://api-sepolia.arbiscan.io/api",
          browserURL: "https://sepolia.arbiscan.io",
        },
      },
      // Celo
      {
        network: "celo",
        chainId: 42220,
        urls: {
          apiURL: "https://api.celoscan.io/api",
          browserURL: "https://celoscan.io",
        },
      },
      {
        network: "celoAlfajores",
        chainId: 44787,
        urls: {
          apiURL: "https://api-alfajores.celoscan.io/api",
          browserURL: "https://alfajores.celoscan.io",
        },
      },
      // Scroll
      {
        network: "scroll",
        chainId: 534352,
        urls: {
          apiURL: "https://api.scrollscan.com/api",
          browserURL: "https://scrollscan.com",
        },
      },
      {
        network: "scrollSepolia",
        chainId: 534351,
        urls: {
          apiURL: "https://api-sepolia.scrollscan.com/api",
          browserURL: "https://sepolia.scrollscan.com",
        },
      },
    ],
  },
  gasReporter: {
    enabled: process.env.REPORT_GAS === "true",
    currency: "USD",
  },
  sourcify: {
    enabled: true,
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};

export default config;
