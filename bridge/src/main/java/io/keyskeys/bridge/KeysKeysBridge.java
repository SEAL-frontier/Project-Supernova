package io.keyskeys.bridge;

import com.google.gson.*;
import io.papermc.paper.event.player.AsyncChatEvent;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer;
import org.bukkit.Bukkit;
import org.bukkit.command.*;
import org.bukkit.entity.Player;
import org.bukkit.event.*;
import org.bukkit.plugin.java.JavaPlugin;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.regex.Pattern;

public final class KeysKeysBridge extends JavaPlugin implements Listener {
 private final Gson gson=new Gson();
 private final ScheduledExecutorService io=Executors.newScheduledThreadPool(3);
 private final Map<UUID,Long> following=new ConcurrentHashMap<>();
 private final Map<String,JsonObject> journal=new LinkedHashMap<>();
 private final Set<String> inflight=ConcurrentHashMap.newKeySet();
 private volatile WebSocket socket; private volatile boolean connecting=false,closing=false;
 private CompletableFuture<?> sendQueue=CompletableFuture.completedFuture(null);
 private Path root,journalFile; private String serverId,endpoint,token;
 private volatile List<String> triggers=List.of("kei");
 private final Map<UUID,List<String>> learnedAliases=new ConcurrentHashMap<>();

 @Override public void onEnable(){
  saveDefaultConfig();serverId=getConfig().getString("server-id","");endpoint=getConfig().getString("endpoint","");token=getConfig().getString("token","");
  triggers=getConfig().getStringList("triggers");if(triggers.isEmpty())triggers=List.of("kei");
  root=getServer().getWorldContainer().toPath().toAbsolutePath().normalize();journalFile=getDataFolder().toPath().resolve("receipts.json");
  try {if(Files.exists(journalFile)){JsonObject saved=JsonParser.parseString(Files.readString(journalFile)).getAsJsonObject();for(var entry:saved.entrySet())journal.put(entry.getKey(),entry.getValue().getAsJsonObject());}}catch(Exception e){getLogger().warning("Receipt journal unreadable; mutations are disabled until repaired.");closing=true;}
  getServer().getPluginManager().registerEvents(this,this);
  if(serverId.isBlank()||endpoint.isBlank()||token.isBlank()){getLogger().warning("Not paired. Run keys-keys server add --kind bridge and copy generated config.yml. No host API or model runs in this plugin.");return;}
  io.scheduleWithFixedDelay(this::connect,0,5,TimeUnit.SECONDS);
  getLogger().info("KEYS_BRIDGE_ENABLED version="+getDescription().getVersion()+" server="+serverId);
 }
 @Override public void onDisable(){closing=true;WebSocket ws=socket;if(ws!=null)ws.sendClose(1000,"server stopping");io.shutdownNow();}
 private void connect(){
  if(closing||connecting||(socket!=null&&!socket.isOutputClosed()))return;connecting=true;
  try {
   URI uri=URI.create(endpoint+(endpoint.contains("?")?"&":"?")+"server="+URLEncoder.encode(serverId,StandardCharsets.UTF_8));
   HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build().newWebSocketBuilder().header("Authorization","Bearer "+token).connectTimeout(Duration.ofSeconds(10)).buildAsync(uri,new Listener()).whenComplete((ws,error)->{connecting=false;if(error!=null){socket=null;getLogger().fine("Bridge reconnect pending: "+error.getClass().getSimpleName());}});
  }catch(Exception e){connecting=false;socket=null;getLogger().warning("Invalid bridge endpoint: "+e.getClass().getSimpleName());}
 }
 private final class Listener implements WebSocket.Listener {
  private final StringBuilder buffer=new StringBuilder();
  @Override public void onOpen(WebSocket ws){socket=ws;ws.request(1);Bukkit.getScheduler().runTask(KeysKeysBridge.this,()->{
   JsonObject hello=obj("type","hello","protocol",1,"version",getDescription().getVersion(),"minecraft_version",Bukkit.getMinecraftVersion(),"authenticated_sessions",true);
   hello.add("capabilities",gson.toJsonTree(List.of("status","players","tps","health","logs","plugins","console","files","plugin_install","profiler")));
   send(hello);getLogger().info("KEYS_BRIDGE_CONNECTED protocol=1");
  });}
  @Override public CompletionStage<?> onText(WebSocket ws,CharSequence data,boolean last){
   buffer.append(data);if(buffer.length()>95*1024*1024){ws.abort();return null;}
   if(last){String text=buffer.toString();buffer.setLength(0);try{JsonObject msg=JsonParser.parseString(text).getAsJsonObject();if(str(msg,"type","").equals("rpc.request"))io.execute(()->rpc(msg));else if(str(msg,"type","").equals("config")){if(msg.has("triggers")){List<String> names=new ArrayList<>();for(JsonElement name:msg.getAsJsonArray("triggers"))names.add(name.getAsString());triggers=List.copyOf(names);}learnedAliases.clear();if(msg.has("aliases_by_uuid"))for(var entry:msg.getAsJsonObject("aliases_by_uuid").entrySet()){List<String> names=new ArrayList<>();for(JsonElement name:entry.getValue().getAsJsonArray())names.add(name.getAsString());learnedAliases.put(UUID.fromString(entry.getKey()),List.copyOf(names));}}}catch(Exception ignored){}}
   ws.request(1);return CompletableFuture.completedFuture(null);
  }
  @Override public CompletionStage<?> onClose(WebSocket ws,int status,String reason){if(socket==ws)socket=null;return CompletableFuture.completedFuture(null);}
  @Override public void onError(WebSocket ws,Throwable error){if(socket==ws)socket=null;}
 }
 private synchronized void send(JsonObject value){WebSocket ws=socket;if(ws!=null&&!ws.isOutputClosed())sendQueue=sendQueue.handle((v,e)->null).thenCompose(v->ws.sendText(gson.toJson(value),true)).exceptionally(e->null);}
 private JsonObject obj(Object... pairs){JsonObject out=new JsonObject();for(int i=0;i<pairs.length;i+=2)out.add(String.valueOf(pairs[i]),gson.toJsonTree(pairs[i+1]));return out;}
 private String str(JsonObject value,String key,String fallback){return value.has(key)&&!value.get(key).isJsonNull()?value.get(key).getAsString():fallback;}
 private boolean bool(JsonObject value,String key){return value.has(key)&&!value.get(key).isJsonNull()&&value.get(key).getAsBoolean();}
 private boolean authenticated(Player player){
  if(Bukkit.getOnlineMode())return true;
  if(Bukkit.getPluginManager().isPluginEnabled("AuthMe"))try {
   Class<?> api=Class.forName("fr.xephi.authme.api.v3.AuthMeApi");Object instance=api.getMethod("getInstance").invoke(null);
   return instance!=null&&(Boolean)api.getMethod("isAuthenticated",Player.class).invoke(instance,player);
  }catch(Exception ignored){return false;}
  // Offline UUIDs alone are not authentication. Conversation is still allowed.
  return false;
 }
 private String discordId(Player player){
  if(!authenticated(player)||!Bukkit.getPluginManager().isPluginEnabled("DiscordSRV"))return null;
  try {Class<?> api=Class.forName("github.scarsz.discordsrv.DiscordSRV");Object plugin=api.getMethod("getPlugin").invoke(null);Object manager=api.getMethod("getAccountLinkManager").invoke(plugin);Object result=manager.getClass().getMethod("getDiscordId",UUID.class).invoke(manager,player.getUniqueId());return result==null?null:result.toString();}catch(Exception ignored){return null;}
 }
 private boolean called(UUID actor,String text){String lower=text.toLowerCase(Locale.ROOT);List<String> names=new ArrayList<>(triggers);names.addAll(learnedAliases.getOrDefault(actor,List.of()));for(String trigger:names)if(Pattern.compile("(?U)(?<!\\w)"+Pattern.quote(trigger.toLowerCase(Locale.ROOT))+"(?!\\w)").matcher(lower).find())return true;return false;}
 @EventHandler(priority=EventPriority.MONITOR,ignoreCancelled=true) public void chat(AsyncChatEvent event){
  String text=PlainTextComponentSerializer.plainText().serialize(event.originalMessage());UUID id=event.getPlayer().getUniqueId();
  if(!called(id,text)&&following.getOrDefault(id,0L)<System.currentTimeMillis())return;
  Bukkit.getScheduler().runTask(this,()->{Player player=Bukkit.getPlayer(id);if(player!=null)emit(player,"chat",text,true);});
 }
 private void emit(Player player,String command,String text,boolean publicChat){
  if(socket==null||socket.isOutputClosed()){player.sendMessage(Component.text("Kei đang offline; chưa nhận hay thực thi yêu cầu nào."));return;}
  following.put(player.getUniqueId(),System.currentTimeMillis()+90000);
  JsonObject message=obj("type","chat","id",UUID.randomUUID().toString(),"uuid",player.getUniqueId().toString(),"name",player.getName(),"command",command,"message",text,"public",publicChat,"authenticated",authenticated(player));
  String discord=discordId(player);if(discord!=null)message.addProperty("discord_id",discord);send(message);
 }
 @Override public boolean onCommand(CommandSender sender,Command command,String label,String[] args){
  if(command.getName().equalsIgnoreCase("keibridge")){
   if(!sender.hasPermission("keyskeys.bridge.admin"))return true;
   sender.sendMessage("KeysKeysBridge "+getDescription().getVersion()+" online="+(socket!=null&&!socket.isOutputClosed())+" protocol=1 minecraft="+Bukkit.getMinecraftVersion());return true;
  }
  if(!(sender instanceof Player player)){sender.sendMessage("/kei needs a player. Use keibridge for connection health.");return true;}
  if(args.length==0){sender.sendMessage("/kei <message> | /kei link <code> | /kei confirm <task> | /kei debug off|minimal|advanced");return true;}
  String first=args[0].toLowerCase(Locale.ROOT);boolean control=List.of("link","confirm","debug","privacy","persona","dm","unlink").contains(first);
  emit(player,control?first:"chat",String.join(" ",control?Arrays.copyOfRange(args,1,args.length):args),false);return true;
 }
 private void rpc(JsonObject request){
  String id=str(request,"id",""),method=str(request,"method","");JsonObject args=request.has("args")?request.getAsJsonObject("args"):new JsonObject();boolean mutation=!str(request,"effect","read").equals("read");
  if(id.isBlank())return;
  synchronized(journal){
   if(journal.containsKey(id)){
    JsonObject old=journal.get(id);JsonObject result=old.has("result")?old.getAsJsonObject("result"):obj("verified",false,"error","Uncertain prior mutation; inspect actual state before retry");send(obj("type","rpc.result","id",id,"result",result));return;
   }
   if(!inflight.add(id))return;
   if(mutation){journal.put(id,obj("status","started"));try{persistJournal();}catch(Exception e){finish(id,obj("error","Could not persist action receipt; not executed","verified",false),false);return;}}
  }
  Runnable action=()->{
   try {
    if(method.equals("console")){console(id,args,mutation);return;}
    JsonObject result;
    if(method.equals("inspect"))result=inspect(args);
    else if(method.equals("files"))result=files(args);
    else if(method.equals("chat.send")||method.equals("chat.progress")){
     Player player=Bukkit.getPlayer(UUID.fromString(str(args,"uuid","")));String text=str(args,"text","");
     if(method.equals("chat.progress")){if(player!=null)player.sendActionBar(Component.text(text));}
     else if(bool(args,"public"))Bukkit.broadcast(Component.text("[Kei] "+text));
     else if(player!=null)player.sendMessage(Component.text("[Kei] "+text));
     result=obj("verified",player!=null||bool(args,"public"),"delivered",player!=null||bool(args,"public"));
    }else result=obj("verified",false,"error","Unsupported bridge method");
    finish(id,result,mutation);
   }catch(Exception e){finish(id,obj("verified",false,"error",e.getClass().getSimpleName()+": "+e.getMessage()),mutation);}
  };
  if(method.equals("files")||(method.equals("inspect")&&str(args,"kind","").equals("logs")))action.run();else Bukkit.getScheduler().runTask(this,action);
 }
 private void finish(String id,JsonObject result,boolean mutation){
  result.addProperty("observed_at",System.currentTimeMillis()/1000.0);result.addProperty("target",serverId);
  Runnable done=()->{if(mutation)synchronized(journal){journal.put(id,obj("status","done","result",result));while(journal.size()>3000)journal.remove(journal.keySet().iterator().next());try{persistJournal();}catch(Exception e){getLogger().warning("Receipt persistence failed after action; reconcile before retry.");}}inflight.remove(id);send(obj("type","rpc.result","id",id,"result",result));};
  if(!io.isShutdown())io.execute(done);
 }
 private void persistJournal() throws IOException {Files.createDirectories(journalFile.getParent());Path temp=journalFile.resolveSibling("receipts.tmp");Files.writeString(temp,gson.toJson(journal));Files.move(temp,journalFile,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}
 private JsonObject inspect(JsonObject args) throws Exception {
  String kind=str(args,"kind","status");Runtime runtime=Runtime.getRuntime();long used=runtime.totalMemory()-runtime.freeMemory();
  if(kind.equals("logs")){String text=tail(root.resolve("logs/latest.log"),120000);return obj("verified",true,"stdout",text);}
  if(kind.equals("plugins"))return obj("verified",true,"stdout",Arrays.stream(Bukkit.getPluginManager().getPlugins()).map(p->p.getName()+" "+p.getDescription().getVersion()+" enabled="+p.isEnabled()).reduce("",(a,b)->a+b+"\n"));
  List<Map<String,Object>> players=Bukkit.getOnlinePlayers().stream().map(p->Map.<String,Object>of("uuid",p.getUniqueId().toString(),"name",p.getName(),"authenticated",authenticated(p))).toList();
  Map<String,Object> resources=Map.of("memory_bytes",used,"memory_limit_bytes",runtime.maxMemory());
  JsonObject data=obj("state","running","resources",resources,"players",players,"tps",Bukkit.getTPS(),"mspt",Bukkit.getAverageTickTime(),"minecraft_version",Bukkit.getMinecraftVersion(),"memory_scope","JVM heap, not entire host RAM");
  return obj("verified",true,"data",data,"console_output",gson.toJson(data));
 }
 private void console(String id,JsonObject args,boolean mutation){
  String text=str(args,"command","").strip().replaceFirst("^/","");if(text.contains("\n")||text.contains("\r")){finish(id,obj("verified",false,"error","One command per request"),mutation);return;}
  List<String> output=Collections.synchronizedList(new ArrayList<>());ConsoleCommandSender original=Bukkit.getConsoleSender();
  ConsoleCommandSender capture=(ConsoleCommandSender)java.lang.reflect.Proxy.newProxyInstance(getClassLoader(),new Class<?>[]{ConsoleCommandSender.class},(proxy,method,values)->{
   if(method.getName().equals("sendMessage")&&values!=null){for(Object value:values){if(value instanceof String s)output.add(s);else if(value instanceof String[] strings)output.addAll(Arrays.asList(strings));else if(value instanceof Component c)output.add(PlainTextComponentSerializer.plainText().serialize(c));else if(value instanceof Component[] components)for(Component component:components)output.add(PlainTextComponentSerializer.plainText().serialize(component));}return null;}
   try{return method.invoke(original,values);}catch(InvocationTargetException e){throw e.getCause();}
  });
  boolean dispatched;
  try{dispatched=Bukkit.dispatchCommand(capture,text);}catch(Exception e){finish(id,obj("verified",false,"error",e.getClass().getSimpleName()+": "+e.getMessage()),mutation);return;}
  final boolean accepted=dispatched;
  Bukkit.getScheduler().runTaskLater(this,()->{
   String[] words=text.split("\\s+",3);String name=words[0].replaceFirst("^.*:","").toLowerCase(Locale.ROOT);boolean verified=!mutation&&accepted;String post="read command executed on server thread";
   if(name.equals("kick")&&words.length>1){Player target=Bukkit.getPlayerExact(words[1]);verified=accepted&&(target==null||!target.isOnline());post="target absent after kick command";}
   if(name.equals("ban")&&words.length>1){verified=accepted&&Bukkit.getBanList(org.bukkit.BanList.Type.NAME).isBanned(words[1]);post="name ban list contains target";}
   if(name.equals("pardon")&&words.length>1){verified=accepted&&!Bukkit.getBanList(org.bukkit.BanList.Type.NAME).isBanned(words[1]);post="name ban list excludes target";}
   if(name.equals("whitelist")&&words.length>2&&(words[1].equals("add")||words[1].equals("remove"))){verified=accepted&&(Bukkit.getOfflinePlayer(words[2]).isWhitelisted()==words[1].equals("add"));post="whitelist state read back";}
   JsonObject result=obj("accepted",accepted,"verified",verified,"console_output",String.join("\n",output),"note","Dispatch is not a postcondition for unknown mutations; inspect before finishing.");
   if(verified)result.add("verification",obj("kind","bridge_postcondition","scope",post,"command",text));
   finish(id,result,mutation);
  },2L);
 }
 private Path path(String relative) throws IOException {
  Path value=root.resolve(relative).normalize();if(Path.of(relative).isAbsolute()||!value.startsWith(root)||relative.isBlank())throw new IOException("Path must stay inside server root");
  Path existing=value;while(existing!=null&&!Files.exists(existing))existing=existing.getParent();if(existing==null||!existing.toRealPath().startsWith(root.toRealPath()))throw new IOException("Symlink escapes server root");return value;
 }
 private String hash(byte[] bytes) throws Exception {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}
 private JsonObject files(JsonObject args) throws Exception {
  String action=str(args,"action","read"),relative=str(args,"path","");Path target=path(relative);
  if(action.equals("list")){try(var stream=Files.list(target)){return obj("verified",true,"stdout",String.join("\n",stream.map(p->p.getFileName().toString()).toList()));}}
  if(action.equals("read")){try(InputStream input=Files.newInputStream(target)){return obj("verified",true,"stdout",new String(input.readNBytes(100000),StandardCharsets.UTF_8),"truncated",Files.size(target)>100000);}}
  if(action.equals("binary")){if(Files.size(target)>64*1024*1024)throw new IOException("File exceeds 64 MiB");return obj("verified",true,"base64",Base64.getEncoder().encodeToString(Files.readAllBytes(target)));}
  Path backup=path(".kei-backups/"+System.currentTimeMillis()+"/"+relative);boolean existed=Files.exists(target);
  if(existed){if(!Files.isRegularFile(target))throw new IOException("Only regular files may be changed");Files.createDirectories(backup.getParent());Files.copy(target,backup,StandardCopyOption.COPY_ATTRIBUTES);}
  if(action.equals("remove")){Files.delete(target);return obj("verified",!Files.exists(target),"backup_path",root.relativize(backup).toString());}
  byte[] bytes;
  if(action.equals("restore")){String source=str(args,"backup_path","");if(!source.startsWith(".kei-backups/"))throw new IOException("Use a Kei backup");bytes=Files.readAllBytes(path(source));}
  else if(action.equals("write_binary")){bytes=Base64.getDecoder().decode(str(args,"base64",""));}
  else if(action.equals("write")){bytes=str(args,"content","").getBytes(StandardCharsets.UTF_8);}
  else throw new IOException("Unsupported file action");
  if(bytes.length>64*1024*1024)throw new IOException("Write exceeds 64 MiB");Files.createDirectories(target.getParent());Path temp=target.resolveSibling(target.getFileName()+".kei-new");Files.write(temp,bytes);Files.move(temp,target,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
  return obj("verified",hash(Files.readAllBytes(target)).equals(hash(bytes)),"sha256",hash(bytes),"backup_path",existed?root.relativize(backup).toString():null);
 }
 private String tail(Path file,int cap) throws IOException {
  try(RandomAccessFile reader=new RandomAccessFile(file.toFile(),"r")){long size=reader.length();reader.seek(Math.max(0,size-cap));byte[] bytes=new byte[(int)Math.min(size,cap)];reader.readFully(bytes);return new String(bytes,StandardCharsets.UTF_8);}
 }
}
