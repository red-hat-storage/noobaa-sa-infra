/* Copyright (C) 2023 NooBaa */
'use strict';

/** @type {import('./config')} */
const config = exports;

config.DEFAULT_POOL_TYPE = 'HOSTS';
config.AGENT_RPC_PORT = '9999';
config.AGENT_RPC_PROTOCOL = 'tcp';

config.ENDPOINT_HTTP_SERVER_REQUEST_TIMEOUT = 15 * 60 * 1000;
config.ENDPOINT_HTTP_SERVER_KEEPALIVE_TIMEOUT = 1 * 60 * 1000;

// Enable auto tier2 for TMFS buckets
config.BUCKET_AUTOCONF_TIER2_ENABLED = true;
config.BLOCK_STORE_FS_TMFS_ENABLED = true;
config.BLOCK_STORE_FS_MAPPING_INFO_ENABLED = true;

config.DEDUP_ENABLED = false;
config.IO_CALC_MD5_ENABLED = false;
config.IO_CALC_SHA256_ENABLED = false;

config.MAX_OBJECT_PART_SIZE = 1024 * 1024 * 1024;
config.IO_CHUNK_READ_CACHE_SIZE = 1024 * 1024 * 1024;

config.IO_READ_BLOCK_TIMEOUT = 10 * 60 * 1000;
config.IO_WRITE_BLOCK_TIMEOUT = 10 * 60 * 1000;
config.IO_DELETE_BLOCK_TIMEOUT = 10 * 60 * 1000;
config.IO_REPLICATE_BLOCK_TIMEOUT = 10 * 60 * 1000;

config.NODE_IO_DETENTION_DISABLE = true;
config.NODE_IO_DETENTION_THRESHOLD = 0;

config.CHUNK_SPLIT_AVG_CHUNK = 256 * 1024 * 1024;
config.CHUNK_SPLIT_DELTA_CHUNK = 0;

config.CHUNK_CODER_DIGEST_TYPE = 'none';
config.CHUNK_CODER_FRAG_DIGEST_TYPE = 'none';
config.CHUNK_CODER_COMPRESS_TYPE = 'none';
config.CHUNK_CODER_CIPHER_TYPE = 'none';

config.CHUNK_CODER_REPLICAS = 1;
config.CHUNK_CODER_EC_DATA_FRAGS = 2;
config.CHUNK_CODER_EC_PARITY_FRAGS = 2;
config.CHUNK_CODER_EC_PARITY_TYPE = 'cm256';
config.CHUNK_CODER_EC_TOLERANCE_THRESHOLD = 2;
config.CHUNK_CODER_EC_IS_DEFAULT = true;

// bg workers
config.SCRUBBER_ENABLED = false;
config.REBUILD_NODE_ENABLED = false;
config.AWS_METERING_ENABLED = false;
config.AGENT_BLOCKS_VERIFIER_ENABLED = false;
config.TIERING_TTL_WORKER_ENABLED = true;