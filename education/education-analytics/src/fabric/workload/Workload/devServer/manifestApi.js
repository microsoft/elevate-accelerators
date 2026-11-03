/**
 * Manifest API implementation
 * Handles serving of manifest metadata and package files
 */

const express = require('express');
const fs = require('fs').promises;
const path = require('path');
const expressRateLimit = require('express-rate-limit');

const router = express.Router();
const allowedOrigins = new Set([
  'https://app.fabric.microsoft.com',
  'https://app.powerbi.com',
  'https://msit.fabric.microsoft.com',
  'https://msit.powerbi.com',
]);

function corsHeaders(req) {
  const origin = req.get('Origin');
  return origin && allowedOrigins.has(origin)
    ? { 'Access-Control-Allow-Origin': origin, 'Vary': 'Origin' }
    : {};
}

/**
 * Creates a rate limiter with the specified configuration
 * @param {number} maxRequests - Maximum number of requests per window
 * @param {string} errorMessage - Error message for rate limit exceeded
 * @returns {Object} Rate limiter middleware
 */
function createRateLimit(maxRequestsPerMinute, errorMessage) {
  return expressRateLimit({
    windowMs: 1 * 60 * 1000, // 1 minute
    max: maxRequestsPerMinute,
    message: { error: errorMessage },
    standardHeaders: 'draft-8',
    legacyHeaders: false
  });
}

// Rate limiting configuration for manifest endpoints
const rateLimit = createRateLimit(
  100, // Limit each IP to 100 requests per minute
  'Too many requests to manifest endpoints , please try again later.'
);

/**
 * OPTIONS handler for CORS preflight requests
 */
router.options('/manifests_new{*path}', (req, res) => {
  res.header({
    ...corsHeaders(req),
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400' // 24 hours
  });
  res.sendStatus(204); // No content needed for OPTIONS response
  console.log("[Frontend] Handled CORS preflight request for manifest endpoint.");
});

/**
 * GET /manifests_new/metadata
 * Returns metadata about the manifest
 */
router.get('/manifests_new/metadata', rateLimit, (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'application/json',
    ...corsHeaders(req),
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  });
 
  const devParameters = {
    name: process.env.WORKLOAD_NAME,
    url: process.env.FRONTEND_URL,
    devAADFEAppConfig: {
      appId: process.env.DEV_AAD_CONFIG_FE_APPID,
    },
    devAADAppConfig: {
      appId: process.env.DEV_AAD_CONFIG_BE_APPID,
      audience: process.env.DEV_AAD_CONFIG_BE_AUDIENCE,
      redirectUri: process.env.DEV_AAD_CONFIG_REDIRECT_URI
    },
    //If you enable Sandbox Relaxation, make sure to also enable it in the manifest package and vica versa.
    devSandboxRelaxation: false
  };
 
  res.end(JSON.stringify({ extension: devParameters }));
  console.log("[Frontend] Delivered manifest metainformation successfully.");
});

/**
 * GET /manifests_new
 * Returns the manifest package built before DevGateway registration
 */
router.get('/manifests_new', rateLimit, async (req, res) => {
  try {
    const filePath = path.resolve(__dirname, `../../build/Manifest/${process.env.WORKLOAD_NAME}.${process.env.WORKLOAD_VERSION}.nupkg`);
    // Check if the file exists
    await fs.access(filePath);

    res.status(200).set({
      'Content-Type': 'application/octet-stream',
      'Content-Disposition': `attachment; filename="ManifestPackage.1.0.0.nupkg"`,
      ...corsHeaders(req),
      'Access-Control-Allow-Methods': 'GET',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    });

    res.sendFile(filePath);
    console.log("[Frontend] Delivered manifest package successfully.");
  } catch (err) {
    console.error(`❌ Error: ${err.message}`);
    res.status(500).json({
      error: "Failed to serve manifest package",
      details: err.message
    });
  }
});

module.exports = router;