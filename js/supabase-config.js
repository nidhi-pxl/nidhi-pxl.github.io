/**
 * Supabase Client Configuration & Helper Utilities
 * 
 * IMPORTANT:
 * - Only SUPABASE_URL and SUPABASE_ANON_KEY are stored here.
 * - Secret / service role keys MUST NEVER be placed in this file or any frontend script.
 */

window.SUPABASE_CONFIG = {
  // Replace these placeholder values with your actual Supabase credentials
  SUPABASE_URL: "https://kgssygkdbcwmamlhnrmf.supabase.co",
  SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtnc3N5Z2tkYmN3bWFtbGhucm1mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1NDc4MTgsImV4cCI6MjEwNDEyMzgxOH0.uocZcNdW6DkpwnPX4WtGwJVYx4P5y9jiwZq2P_xUGvM",
  
  // Optional admin UID check for frontend routing/UI display
  ADMIN_UID: "e84b1f57-7c3d-4fde-bcce-25d99b5d77bb",
  
  // Storage Bucket Name
  STORAGE_BUCKET: "portfolio"
};

/**
 * Returns full public CDN URL for a given path in the Supabase 'portfolio' storage bucket.
 * @param {string} path - e.g. "originals/flowers/123.jpg" or "thumbnails/flowers/123.jpg"
 * @returns {string} Full image URL
 */
function getPublicUrl(path) {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const baseUrl = window.SUPABASE_CONFIG.SUPABASE_URL.replace(/\/+$/, '');
  const bucket  = window.SUPABASE_CONFIG.STORAGE_BUCKET;
  const cleanPath = path.replace(/^\/+/, '');
  return `${baseUrl}/storage/v1/object/public/${bucket}/${cleanPath}`;
}

/**
 * Initializes and returns the global Supabase client instance using the JS v2 SDK.
 */
function getSupabaseClient() {
  if (window._supabaseInstance) {
    return window._supabaseInstance;
  }
  if (!window.supabase || typeof window.supabase.createClient !== 'function') {
    console.error('Supabase JS SDK not loaded! Make sure supabase-js@2 script tag is included before this script.');
    return null;
  }
  const config = window.SUPABASE_CONFIG;
  if (!config.SUPABASE_URL || config.SUPABASE_URL.includes('YOUR_SUPABASE_PROJECT_ID')) {
    console.warn('Supabase URL is not configured in js/supabase-config.js');
  }
  window._supabaseInstance = window.supabase.createClient(config.SUPABASE_URL, config.SUPABASE_ANON_KEY);
  return window._supabaseInstance;
}

// Global exports
window.getPublicUrl = getPublicUrl;
window.getSupabaseClient = getSupabaseClient;
