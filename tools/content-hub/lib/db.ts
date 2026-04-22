import Database from "better-sqlite3";
import path from "path";

const DB_PATH = path.join(process.cwd(), "content_hub.db");
const db = new Database(DB_PATH);
db.pragma("journal_mode = WAL");

export default db;
