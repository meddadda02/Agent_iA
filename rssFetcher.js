const Parser = require("rss-parser");
const pg = require("pg");

const parser = new Parser();
const pool = new pg.Pool({
  user: "postgres",
  host: "localhost",
  database: "agent_ai",
  password: "salma",
  port: 5432,
});

const feeds = [
  "https://blog.youtube/rss/", // Works
  "https://support.google.com/youtube/rss", // Broken, will be skipped
  "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw" // Example extra
];

async function fetchFeeds() {
  for (const feedUrl of feeds) {
    try {
      console.log(`🔍 Fetching: ${feedUrl}`);
      const feed = await parser.parseURL(feedUrl);

      if (!feed.items || feed.items.length === 0) {
        console.warn(`⚠️ No items found for ${feedUrl}`);
        continue;
      }

      for (const item of feed.items) {
        await saveToDB({
          title: item.title || "No title",
          link: item.link || "",
          pubDate: item.pubDate || new Date().toISOString(),
          source: feed.title || "Unknown Source"
        });
      }

      console.log(`✅ Saved ${feed.items.length} items from ${feedUrl}`);
    } catch (err) {
      console.error(`❌ Error fetching from ${feedUrl}: ${err.message}`);
    }
  }
  process.exit(0);
}
async function saveToDB(article) {
  try {
    await pool.query(
      `INSERT INTO rules (title, link, published_at, source)
       VALUES ($1, $2, $3, $4)
       ON CONFLICT (link) DO NOTHING`,
      [article.title, article.link, article.pubDate, article.source]
    );
  } catch (err) {
    console.error(`❌ DB Insert Error: ${err.message}`);
  }
}


fetchFeeds();
