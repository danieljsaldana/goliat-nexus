import {fileURLToPath} from 'node:url';

/** Static export under its public WAF route; an empty base path keeps private-only deployments compatible. */
export default {output:'export',outputFileTracingRoot:fileURLToPath(new URL('.',import.meta.url)),trailingSlash:true,poweredByHeader:false,basePath:process.env.NEXT_PUBLIC_BASE_PATH||''};
