package tw.radar.app;

import android.app.*;
import android.os.*;
import android.content.*;
import android.graphics.Color;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private LinearLayout root, items, holdingsItems;
    private TextView status;
    private EditText url;
    private final int ink=Color.rgb(20,32,52), teal=Color.rgb(0,122,110);
    private SharedPreferences prefs;
    @Override public void onCreate(Bundle b) { super.onCreate(b); prefs=getSharedPreferences("radar",MODE_PRIVATE); draw(); }
    private TextView text(String s,int size,int color){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);t.setPadding(4,8,4,8);return t;}
    private void draw(){
        ScrollView sc=new ScrollView(this); root=new LinearLayout(this);root.setOrientation(1);root.setPadding(24,28,24,24);root.setBackgroundColor(Color.rgb(246,248,251));sc.addView(root);setContentView(sc);
        root.addView(text("台股籌碼共振雷達",25,ink));
        root.addView(text("三條件同時成立才列入符合名單；缺資料一律不通過。",14,teal));
        root.addView(text("資料網址（HTTPS JSON）",13,ink));
        url=new EditText(this);url.setSingleLine(true);url.setText(prefs.getString("url","https://raw.githubusercontent.com/joeggininder/TWStockRadar/main/data/latest.json"));url.setHint("https://你的網域/data/latest.json");url.setTextSize(13);root.addView(url);
        Button refresh=new Button(this);refresh.setText("儲存網址並更新");root.addView(refresh);refresh.setOnClickListener(v->{String u=url.getText().toString().trim();prefs.edit().putString("url",u).apply();load(u);});
        status=text("尚未連接資料源。請設定公開 HTTPS JSON 網址。",13,Color.DKGRAY);root.addView(status);
        root.addView(text("同時符合三條件",20,ink));items=new LinearLayout(this);items.setOrientation(1);root.addView(items);
        root.addView(text("判斷條件：法人連買／大戶集中／融資退場",13,Color.DKGRAY));
        drawHoldingsSection();
        String u=prefs.getString("url","https://raw.githubusercontent.com/joeggininder/TWStockRadar/main/data/latest.json");if(!u.isEmpty())load(u);
    }
    private void load(String u){
        if(!u.startsWith("https://")){status.setText("請輸入 HTTPS 網址");return;}
        status.setText("更新中…");
        new Thread(()->{
            try {
                HttpURLConnection c=(HttpURLConnection)new URL(u).openConnection();c.setConnectTimeout(12000);c.setReadTimeout(15000);c.setRequestProperty("Accept","application/json");
                if(c.getResponseCode()!=200)throw new IOException("HTTP "+c.getResponseCode());
                ByteArrayOutputStream buf=new ByteArrayOutputStream();try(InputStream in=c.getInputStream()){byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1){buf.write(b,0,n);if(buf.size()>10000000)throw new IOException("回應過大");}}
                JSONObject j=new JSONObject(buf.toString(StandardCharsets.UTF_8.name()));runOnUiThread(()->render(j));
            }catch(Exception e){runOnUiThread(()->status.setText("更新失敗："+e.getMessage()+"（保留上次畫面）"));}
        }).start();
    }
    
    private void render(JSONObject j) {
        String date = j.optString("generated_at", "未提供");
        JSONArray stocks = j.optJSONArray("stocks");
        items.removeAllViews();

        int fullCount = 0;
        int watchCount = 0;

        LinearLayout watchItems = new LinearLayout(this);
        watchItems.setOrientation(1);

        if (stocks != null) {
            for (int i = 0; i < stocks.length(); i++) {
                JSONObject s = stocks.optJSONObject(i);
                if (s == null) continue;

                JSONObject c = s.optJSONObject("checks");
                if (c == null) continue;

                boolean institutional = c.optBoolean("institutional", false);
                boolean holders = c.optBoolean("holders", false);
                boolean retail = c.optBoolean("retail", false);

                int matched = (institutional ? 1 : 0)
                            + (holders ? 1 : 0)
                            + (retail ? 1 : 0);

                if (matched < 2) continue;

                LinearLayout card = new LinearLayout(this);
                card.setOrientation(1);
                card.setPadding(18, 14, 18, 14);
                card.setBackgroundColor(Color.WHITE);

                card.addView(text(
                    s.optString("id") + "  " + s.optString("name"),
                    20, ink
                ));

                card.addView(text(
                    "收盤價：" + s.optString("close", "缺資料"),
                    14, ink
                ));

                card.addView(text(
                    "法人 " + (institutional ? "✓" : "—") +
                    "  大戶 " + (holders ? "✓" : "—") +
                    "  融資 " + (retail ? "✓" : "—"),
                    14, teal
                ));

                if (matched == 3) {
                    fullCount++;
                    items.addView(card);
                    items.addView(new View(this),
                        new LinearLayout.LayoutParams(1, 14));
                } else {
                    watchCount++;
                    watchItems.addView(card);
                    watchItems.addView(new View(this),
                        new LinearLayout.LayoutParams(1, 14));
                }
            }
        }

        if (fullCount == 0) {
            items.addView(text(
                "目前沒有同時符合三項條件的股票。",
                14, Color.DKGRAY
            ));
        }

        items.addView(text(
            "符合兩項條件的觀察名單（" + watchCount + " 檔）",
            20, ink
        ));

        if (watchCount == 0) {
            items.addView(text(
                "目前沒有符合兩項條件的股票。",
                14, Color.DKGRAY
            ));
        } else {
            items.addView(watchItems);
        }

        status.setText(
            "資料產生時間：" + date +
            "\n三條件符合：" + fullCount + " 檔" +
            "\n兩條件觀察：" + watchCount + " 檔" +
            "\n" + j.optString("notice", "")
        );
    }

    private JSONArray getHoldings() {
        try {
            return new JSONArray(prefs.getString("holdings", "[]"));
        } catch (JSONException e) {
            return new JSONArray();
        }
    }

    private void saveHoldings(JSONArray data) {
        prefs.edit().putString("holdings", data.toString()).apply();
        refreshHoldings();
    }

    private void drawHoldingsSection() {
        root.addView(text("我的持股（僅儲存在手機）", 20, ink));

        Button add = new Button(this);
        add.setText("＋ 新增持股");
        root.addView(add);
        add.setOnClickListener(v -> editHolding(-1));

        holdingsItems = new LinearLayout(this);
        holdingsItems.setOrientation(1);
        root.addView(holdingsItems);
        refreshHoldings();
    }

    private void refreshHoldings() {
        if (holdingsItems == null) return;
        holdingsItems.removeAllViews();

        JSONArray data = getHoldings();

        if (data.length() == 0) {
            holdingsItems.addView(text("尚未新增持股", 14, Color.DKGRAY));
        }

        for (int i = 0; i < data.length(); i++) {
            JSONObject h = data.optJSONObject(i);
            if (h == null) continue;

            final int index = i;
            String period = h.optString("period", "swing");
            String periodName = period.equals("short") ? "短線"
                    : period.equals("long") ? "中長期" : "波段";

            LinearLayout card = new LinearLayout(this);
            card.setOrientation(1);
            card.setPadding(18, 12, 18, 12);
            card.setBackgroundColor(Color.WHITE);

            card.addView(text(
                h.optString("id") + "｜" + periodName, 18, ink
            ));
            card.addView(text(
                "成本：" + h.optString("cost") + " 元｜股數：" +
                h.optString("shares"), 14, ink
            ));

            LinearLayout buttons = new LinearLayout(this);

            Button edit = new Button(this);
            edit.setText("修改");
            edit.setOnClickListener(v -> editHolding(index));
            buttons.addView(edit);

            Button delete = new Button(this);
            delete.setText("刪除");
            delete.setOnClickListener(v ->
                new AlertDialog.Builder(this)
                    .setMessage("確定刪除 " + h.optString("id") + "？")
                    .setNegativeButton("取消", null)
                    .setPositiveButton("刪除", (d, w) -> {
                        JSONArray old = getHoldings();
                        JSONArray next = new JSONArray();
                        for (int k = 0; k < old.length(); k++) {
                            if (k != index) next.put(old.opt(k));
                        }
                        saveHoldings(next);
                    }).show()
            );
            buttons.addView(delete);

            card.addView(buttons);
            holdingsItems.addView(card);

            View gap = new View(this);
            holdingsItems.addView(
                gap, new LinearLayout.LayoutParams(1, 12)
            );
        }
    }

    private EditText holdingField(String hint, String value, int type) {
        EditText field = new EditText(this);
        field.setHint(hint);
        field.setSingleLine(true);
        field.setInputType(type);
        field.setText(value);
        return field;
    }

    private void editHolding(int index) {
        JSONArray data = getHoldings();
        JSONObject old = index >= 0 ? data.optJSONObject(index) : null;
        if (old == null) old = new JSONObject();

        LinearLayout fields = new LinearLayout(this);
        fields.setOrientation(1);
        fields.setPadding(32, 8, 32, 0);

        EditText id = holdingField(
            "股票代號（4 碼）", old.optString("id"), 2
        );
        EditText cost = holdingField(
            "平均成本（元）", old.optString("cost"), 8194
        );
        EditText shares = holdingField(
            "持有股數", old.optString("shares"), 2
        );

        fields.addView(id);
        fields.addView(cost);
        fields.addView(shares);
        fields.addView(text("投資週期", 14, ink));

        Spinner spinner = new Spinner(this);
        String[] options = {"短線", "波段", "中長期"};
        spinner.setAdapter(new ArrayAdapter<String>(
            this, android.R.layout.simple_spinner_dropdown_item, options
        ));

        String previous = old.optString("period", "swing");
        spinner.setSelection(
            previous.equals("short") ? 0 :
            previous.equals("long") ? 2 : 1
        );
        fields.addView(spinner);

        AlertDialog dialog = new AlertDialog.Builder(this)
            .setTitle(index >= 0 ? "修改持股" : "新增持股")
            .setView(fields)
            .setNegativeButton("取消", null)
            .setPositiveButton("儲存", null)
            .create();

        dialog.setOnShowListener(v ->
            dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(btn -> {

                String sid = id.getText().toString().trim();
                String price = cost.getText().toString().trim();
                String amount = shares.getText().toString().trim();

                if (!sid.matches("[0-9]{4}")) {
                    id.setError("請輸入 4 碼股票代號");
                    return;
                }

                double costValue;
                long shareValue;

                try {
                    costValue = Double.parseDouble(price);
                    shareValue = Long.parseLong(amount);

                    if (Double.isNaN(costValue) ||
                        Double.isInfinite(costValue) ||
                        costValue <= 0 || shareValue <= 0) {
                        throw new NumberFormatException();
                    }
                } catch (NumberFormatException e) {
                    cost.setError("請輸入有效的正數成本與整數股數");
                    return;
                }

                JSONArray current = getHoldings();

                for (int i = 0; i < current.length(); i++) {
                    JSONObject h = current.optJSONObject(i);
                    if (i != index && h != null &&
                        sid.equals(h.optString("id"))) {
                        id.setError("股票已存在，請使用修改功能");
                        return;
                    }
                }

                JSONObject item = new JSONObject();

                try {
                    item.put("id", sid);
                    item.put("cost", costValue);
                    item.put("shares", shareValue);
                    item.put("period",
                        spinner.getSelectedItemPosition() == 0 ? "short" :
                        spinner.getSelectedItemPosition() == 2 ? "long" :
                        "swing"
                    );

                    if (index >= 0) {
                        current.put(index, item);
                    } else {
                        current.put(item);
                    }

                    saveHoldings(current);
                    dialog.dismiss();

                } catch (JSONException e) {
                    Toast.makeText(
                        this, "儲存失敗", Toast.LENGTH_SHORT
                    ).show();
                }
            })
        );

        dialog.show();
    }

}
