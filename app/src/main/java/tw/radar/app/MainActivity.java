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
    private LinearLayout root, items;
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
        String u=prefs.getString("url","https://raw.githubusercontent.com/joeggininder/TWStockRadar/main/data/latest.json");if(!u.isEmpty())load(u);
    }
    private void load(String u){
        if(!u.startsWith("https://")){status.setText("請輸入 HTTPS 網址");return;}
        status.setText("更新中…");
        new Thread(()->{
            try {
                HttpURLConnection c=(HttpURLConnection)new URL(u).openConnection();c.setConnectTimeout(12000);c.setReadTimeout(15000);c.setRequestProperty("Accept","application/json");
                if(c.getResponseCode()!=200)throw new IOException("HTTP "+c.getResponseCode());
                ByteArrayOutputStream buf=new ByteArrayOutputStream();try(InputStream in=c.getInputStream()){byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1){buf.write(b,0,n);if(buf.size()>2000000)throw new IOException("回應過大");}}
                JSONObject j=new JSONObject(buf.toString(StandardCharsets.UTF_8.name()));runOnUiThread(()->render(j));
            }catch(Exception e){runOnUiThread(()->status.setText("更新失敗："+e.getMessage()+"（保留上次畫面）"));}
        }).start();
    }
    private void render(JSONObject j){
        String date=j.optString("generated_at","未提供");JSONArray stocks=j.optJSONArray("stocks");items.removeAllViews();int count=0;
        if(stocks!=null)for(int i=0;i<stocks.length();i++){
            JSONObject s=stocks.optJSONObject(i);if(s==null)continue;
            JSONObject c=s.optJSONObject("checks");if(c==null)continue;
           boolean all=c.optBoolean("institutional",false)&&c.optBoolean("holders",false)&&c.optBoolean("retail",false);
            if(!all)continue;count++;
            LinearLayout card=new LinearLayout(this);card.setOrientation(1);card.setPadding(18,14,18,14);card.setBackgroundColor(Color.WHITE);
            card.addView(text(s.optString("id")+"  "+s.optString("name"),20,ink));
            card.addView(text("收盤價："+s.optString("close","缺資料")+"｜交易日："+s.optString("trade_date","缺資料"),14,ink));
            card.addView(text("法人 ✓  大戶 ✓  融資 ✓",14,teal));
            card.addView(text(s.optString("evidence","詳情缺資料"),13,Color.DKGRAY));
            items.addView(card);View space=new View(this);items.addView(space,new LinearLayout.LayoutParams(1,14));
        }
       if(count==0)items.addView(text("目前沒有可驗證、同時符合三項條件的股票。這不代表市場上一定沒有，而是已取得資料中沒有確認符合者。",14,Color.DKGRAY));
        status.setText("資料產生時間："+date+"｜已確認符合："+count+" 檔。\n"+j.optString("notice",""));
    }
}
