# Meta Ads Setup Checklist — Coach Campaign Pillar 5

**Goal:** Get your Meta Business Manager + Ad Account + Marketing API token ready for the daily creative iteration loop.

**Before starting:** Have a card ready for payment method. This is a ₱5K/mo (PHP) campaign targeting PH-domestic coaches.

---

## Step 1: Create Meta Business Manager

1. Go to **https://business.facebook.com**
2. Click **"Create Account"**
3. Enter business name: `Enriquez — Aristotle AI Agency Package` (or your preferred brand name)
4. Add your business email (recommended: your personal .ai email)
5. Add your name and select country (PH if managing from PH, or your primary location)
6. Click **Create Business**
7. You'll land on the Business Dashboard. Bookmark it.

**Gate:** Verify you're logged in and see "Accounts" in the left menu. Continue below when confirmed.

---

## Step 2: Create Ad Account

1. In Business Dashboard, go to **Settings** (bottom left)
2. Select **"Ad accounts"** from the left menu
3. Click **"Add"** → **"Create new ad account"**
4. **Account name:** `coach-pillar5-ph`
5. **Currency:** **PHP** (critical for ₱5K/mo tracking)
6. **Timezone:** **Asia/Manila**
7. **Account industry:** Select "Marketing Agency" or "Coaching/Training"
8. Click **Create**
9. You'll see a new Ad Account ID like `act_123456789`. **Copy this and save it** — you'll need it in Step 6.

**Gate:** Verify the ad account appears in your Ad accounts list. Status should say "Active."

---

## Step 3: Add Payment Method

1. In the Business Dashboard, go to **Settings** > **Billing**
2. Click **"Payment methods"**
3. Click **"Add"** → **"Debit or credit card"**
4. Enter your card details (Visa/MC accepted for PH)
5. Billing country: **Philippines** (matches your timezone and campaign scope)
6. Enter billing address
7. Click **"Save"**
8. Meta may send a verification charge (~₱1-10); check your email and confirm

**Gate:** Your payment method status should say "Active" within 5 minutes.

---

## Step 4: Connect Your Facebook Page

Your Facebook page is: `profile.php?id=61574343211417`

1. In Business Dashboard, go to **Settings** > **Instagram accounts** (or **Facebook pages** if you only have a Page, no IG account)
2. Click **"Add"**
3. Select your personal brand page from the dropdown (the one with ID ending in ...11417)
4. Grant permissions when prompted
5. Click **"Save"**

**Gate:** Your page appears in the list with a green checkmark. Proceed when confirmed.

---

## Step 5: Create a System User (Recommended) OR Use Temporary User Token

### Option A: System User (Recommended — no expiry)

1. Go to **Settings** > **Users** (left menu)
2. Click **"System users"** tab
3. Click **"Create system user"**
4. **Name:** `enriquez-claude-ads-api`
5. **Role:** Select "Admin"
6. Click **Create**
7. Click on the user you just created
8. Click **"Generate new token"**
9. **Validity:** Select "Never expires" (important for unattended cron jobs)
10. **App:** Click "Select apps" → Select your ad account or create a test app
11. Check these scopes:
    - `ads_management`
    - `ads_read`
    - `business_management`
12. Click **"Generate token"**
13. **Copy the token immediately** and save it securely (see Step 6)

**Gate:** Token is copied and saved. You won't see it again.

### Option B: Temporary User Token (if System User unavailable)

1. Go to **https://developers.facebook.com/tools/explorer**
2. Log in with your Facebook account
3. In the **"Meta App"** dropdown (top right), create a new test app or select your business app
4. In the **"Get User Access Token"** section, click the blue button
5. In the permission popup, check:
   - `ads_management`
   - `ads_read`
   - `business_management`
6. Click **"Generate Token"**
7. Copy the token immediately

**Caveat:** User tokens expire every 60 days. Set a calendar reminder to refresh. (System user is better.)

**Gate:** Token copied and saved.

---

## Step 6: Save Credentials to `.env`

1. Open `projects/personal/.env` in your editor
2. Add these lines (or update if they exist):

```
META_ADS_TOKEN=your_token_here
META_AD_ACCOUNT_ID=act_your_account_id_here
META_PAGE_ID=61574343211417
META_CAMPAIGN_NAME=coach-pillar5-ph
```

**Replace:**
- `your_token_here` with the token from Step 5
- `your_account_id_here` with the ID from Step 2 (without the `act_` prefix; the script will add it)

**Gate:** Save the file. Do not commit `.env` to git.

---

## Step 7: Verify API Access

Open your terminal and run:

```bash
export META_ADS_TOKEN="$(grep META_ADS_TOKEN /Users/allenenriquez/projects/personal/.env | cut -d= -f2)"
export META_AD_ACCOUNT_ID="$(grep META_AD_ACCOUNT_ID /Users/allenenriquez/projects/personal/.env | cut -d= -f2)"

curl -s "https://graph.facebook.com/v19.0/${META_AD_ACCOUNT_ID}/insights?fields=spend,impressions&access_token=${META_ADS_TOKEN}&date_preset=yesterday" | head -20
```

**Expected output:** JSON response with `insights` array (even if empty for new account). **NOT** an error like "Invalid OAuth token" or "Unsupported get request."

**Gate:** Verify you see `"insights"` in the response, not an error. If error:
- Token may be invalid or have wrong scopes — regenerate in Step 5
- Account ID may be wrong — double-check in Step 2
- Currency may not be PHP — check in Step 2 again

---

## Step 8: Common Gotchas

| Issue | Fix |
|---|---|
| "Unsupported get request" error | Token is missing `ads_read` scope. Regenerate token in Step 5 and check all three scopes. |
| "Invalid currency" when creating account | Retry Step 2, ensure you select PHP before clicking Create. |
| Token expires after 60 days | You used Option B (temporary token). System user (Option A) doesn't expire. Regenerate now or switch to Option A. |
| Page won't connect in Step 4 | Ensure you're the admin of the page. Verify page ID matches `61574343211417`. |
| Ad account not showing in ad interface | Wait 5 minutes after creation. Hard refresh your browser (Cmd+Shift+R). |
| Rate limit errors (429) during loop | Space requests 3-5 sec apart. The loop script handles this. |

---

## You're Ready

Once Step 7 verification passes, your setup is complete. The daily ad iteration loop (`tools/personal/ad_iterator.py`) can now:
- Read metrics from yesterday's ads
- Generate new variants
- Push new creatives to Meta
- Pause underperformers

**Next:** Share the credentials with the Claude Code cron that runs `tools/personal/ad_iterator.py` on launchd, or run it manually to test.

---

## Reference: Graph API Versions

This checklist uses **Graph API v19.0** (released Feb 2024, stable through 2025). If Meta deprecates it, check https://developers.facebook.com/docs/graph-api/changelog for the current version and update the curl command in Step 7.
