// DiaScope mobile app v2 (React Native / Expo): login, tabs, explore, insights, history, model info.
import React, { useState, useEffect } from "react";
import { View, Text, TextInput, ScrollView, TouchableOpacity, Switch, ActivityIndicator, StatusBar, Platform, Share } from "react-native";

const LIGHT = { bg: "#F4F8F7", card: "#FFFFFF", text: "#12302D", muted: "#5B6F6C", teal: "#0F766E", onTeal: "#FFFFFF", border: "#DCE9E6", input: "#FFFFFF" };
const DARK = { bg: "#0B1B1A", card: "#13302D", text: "#E6F4F1", muted: "#9CC5BF", teal: "#2DD4BF", onTeal: "#06201E", border: "#1F4A45", input: "#16403B" };
const LEVEL = { Low: "#16A34A", Moderate: "#D97706", High: "#DC2626" };
const CORAL = "#F97316", GREY = "#94A3B8";
const DEFAULT_FORM = { age: 7, health: 3, height: "165", weight: "70", income: 7, phys: 0, exercise: true, walk: false, heart: false };

const card = (C) => ({ backgroundColor: C.card, borderRadius: 16, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: C.border });
const H = ({ C, children }) => <Text style={{ color: C.text, fontSize: 17, fontWeight: "700", marginBottom: 6 }}>{children}</Text>;
const Muted = ({ C, children, style }) => <Text style={[{ color: C.muted, fontSize: 12, marginBottom: 6 }, style]}>{children}</Text>;

function Btn({ title, onPress, C, busy, ghost }) {
  return (
    <TouchableOpacity onPress={onPress} style={{ backgroundColor: ghost ? "transparent" : C.teal, borderWidth: 1, borderColor: C.teal, borderRadius: 12, padding: 13, alignItems: "center", marginTop: 10 }}>
      {busy ? <ActivityIndicator color={ghost ? C.teal : C.onTeal} /> : <Text style={{ color: ghost ? C.teal : C.onTeal, fontWeight: "700", fontSize: 15 }}>{title}</Text>}
    </TouchableOpacity>
  );
}

function Field({ C, label, ...props }) {
  return (
    <View>
      <Text style={{ color: C.text, fontWeight: "600", marginTop: 12, marginBottom: 6 }}>{label}</Text>
      <TextInput {...props} placeholderTextColor={C.muted} autoCapitalize="none" autoCorrect={false}
        style={{ backgroundColor: C.input, color: C.text, borderWidth: 1, borderColor: C.border, borderRadius: 10, padding: 10, fontSize: 16 }} />
    </View>
  );
}

function Chips({ options, value, onChange, C }) {
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap" }}>
      {options.map((label, i) => {
        const on = value === i + 1;
        return (
          <TouchableOpacity key={label} onPress={() => onChange(i + 1)}
            style={{ borderWidth: 1, borderColor: C.teal, backgroundColor: on ? C.teal : "transparent", borderRadius: 20, paddingVertical: 6, paddingHorizontal: 12, marginRight: 6, marginBottom: 6 }}>
            <Text style={{ color: on ? C.onTeal : C.text, fontSize: 13 }}>{label}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function Row({ label, value, onChange, C }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 6 }}>
      <Text style={{ color: C.text, fontSize: 15, flex: 1, paddingRight: 10 }}>{label}</Text>
      <Switch value={value} onValueChange={onChange} trackColor={{ true: C.teal, false: C.border }} />
    </View>
  );
}

function Stepper({ value, onChange, min, max, step = 1, C }) {
  const btn = { borderWidth: 1, borderColor: C.teal, borderRadius: 8, width: 38, height: 38, alignItems: "center", justifyContent: "center" };
  return (
    <View style={{ flexDirection: "row", alignItems: "center" }}>
      <TouchableOpacity style={btn} onPress={() => onChange(Math.max(min, value - step))}><Text style={{ color: C.teal, fontSize: 20 }}>-</Text></TouchableOpacity>
      <Text style={{ color: C.text, fontSize: 18, fontWeight: "700", marginHorizontal: 16 }}>{value}</Text>
      <TouchableOpacity style={btn} onPress={() => onChange(Math.min(max, value + step))}><Text style={{ color: C.teal, fontSize: 20 }}>+</Text></TouchableOpacity>
    </View>
  );
}

function BarChart({ labels, series, C, height = 110, max }) {
  const m = max || Math.max(1, ...series.flatMap((s) => s.values.map((v) => v || 0)));
  return (
    <View>
      <View style={{ flexDirection: "row", alignItems: "flex-end", height }}>
        {labels.map((l, i) => (
          <View key={i} style={{ flex: 1, flexDirection: "row", alignItems: "flex-end", justifyContent: "center", height }}>
            {series.map((s, j) => (
              <View key={j} style={{ width: series.length > 1 ? "38%" : "62%", height: Math.max(2, ((s.values[i] || 0) / m) * height), backgroundColor: s.color, marginHorizontal: 1, borderTopLeftRadius: 3, borderTopRightRadius: 3 }} />
            ))}
          </View>
        ))}
      </View>
      <View style={{ flexDirection: "row", marginTop: 3 }}>
        {labels.map((l, i) => <Text key={i} style={{ flex: 1, textAlign: "center", fontSize: 9, color: C.muted }}>{l}</Text>)}
      </View>
    </View>
  );
}

function Legend({ items, C }) {
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 6 }}>
      {items.map(([name, color]) => (
        <View key={name} style={{ flexDirection: "row", alignItems: "center", marginRight: 14 }}>
          <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: color, marginRight: 5 }} />
          <Text style={{ color: C.muted, fontSize: 11 }}>{name}</Text>
        </View>
      ))}
    </View>
  );
}

function Meter({ percent, meta, C }) {
  const low = (meta && meta.levels ? meta.levels.low_below : 0.1) * 100, high = (meta && meta.levels ? meta.levels.high_from : 0.25) * 100;
  const top = Math.max(60, Math.ceil(percent / 10) * 10);
  return (
    <View style={{ width: "100%", marginVertical: 12 }}>
      <View style={{ flexDirection: "row", height: 14, borderRadius: 7, overflow: "hidden" }}>
        <View style={{ flex: low, backgroundColor: "#BBF7D0" }} />
        <View style={{ flex: high - low, backgroundColor: "#FDE68A" }} />
        <View style={{ flex: Math.max(1, top - high), backgroundColor: "#FECACA" }} />
      </View>
      <View style={{ position: "absolute", left: Math.min(98, (percent / top) * 100) + "%", top: -4, width: 4, height: 22, backgroundColor: C.text, borderRadius: 2 }} />
      <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: 4 }}>
        <Text style={{ color: C.muted, fontSize: 10 }}>Low</Text><Text style={{ color: C.muted, fontSize: 10 }}>Moderate</Text><Text style={{ color: C.muted, fontSize: 10 }}>High</Text>
      </View>
    </View>
  );
}

function TRow({ cells, C, head }) {
  return (
    <View style={{ flexDirection: "row", paddingVertical: 5, borderBottomWidth: 1, borderBottomColor: C.border }}>
      {cells.map((c, i) => <Text key={i} style={{ flex: i === 0 ? 1.6 : 1, color: head ? C.teal : C.text, fontWeight: head ? "700" : "400", fontSize: 12 }}>{c}</Text>)}
    </View>
  );
}

// ---------------------------------------------------------------- screens
export function Welcome({ C, onAccept }) {
  return (
    <View style={card(C)}>
      <H C={C}>Before you start</H>
      <Text style={{ color: C.text, lineHeight: 21 }}>
        DiaScope estimates diabetes risk from a few health answers, using patterns in the CDC BRFSS 2024 survey of 441,934 adults.{"\n\n"}
        It is a screening aid and not a medical diagnosis. Only a doctor and a blood test can confirm diabetes.{"\n\n"}
        Your saved results stay on your own server. No ads, no sharing.
      </Text>
      <Btn title="I understand" onPress={onAccept} C={C} />
    </View>
  );
}

export function ConnectScreen({ C, server, setServer, onConnect, busy }) {
  return (
    <View style={card(C)}>
      <H C={C}>Connect to the DiaScope server</H>
      <Muted C={C}>Type your laptop address, for example http://192.168.1.115:8000 (same Wi-Fi as this phone).</Muted>
      <Field C={C} label="Server address" value={server} onChangeText={setServer} />
      <Btn title="Connect" onPress={onConnect} C={C} busy={busy} />
    </View>
  );
}

export function AuthScreen({ C, onLogin, onRegister, busy }) {
  const [mode, setMode] = useState("login");
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [p2, setP2] = useState("");
  return (
    <View style={card(C)}>
      <View style={{ flexDirection: "row", marginBottom: 6 }}>
        {[["login", "Log in"], ["register", "Create account"]].map(([k, t]) => (
          <TouchableOpacity key={k} onPress={() => setMode(k)} style={{ flex: 1, paddingVertical: 10, borderBottomWidth: 2, borderBottomColor: mode === k ? C.teal : C.border, alignItems: "center" }}>
            <Text style={{ color: mode === k ? C.teal : C.muted, fontWeight: "700" }}>{t}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <Field C={C} label="Username" value={u} onChangeText={setU} />
      <Field C={C} label="Password" value={p} onChangeText={setP} secureTextEntry />
      {mode === "register" ? <Field C={C} label="Repeat the password" value={p2} onChangeText={setP2} secureTextEntry /> : null}
      <Btn C={C} busy={busy} title={mode === "login" ? "Log in" : "Create account"}
        onPress={() => (mode === "login" ? onLogin(u, p) : onRegister(u, p, p2, () => setMode("login")))} />
    </View>
  );
}

export function FormView({ C, meta, form, set, onCalculate, busy }) {
  return (
    <View style={card(C)}>
      <H C={C}>Your profile</H>
      <Text style={{ color: C.text, fontWeight: "600", marginBottom: 6 }}>Age group</Text>
      <Chips options={meta.age_groups} value={form.age} onChange={set("age")} C={C} />
      <Text style={{ color: C.text, fontWeight: "600", marginTop: 8, marginBottom: 6 }}>General health</Text>
      <Chips options={meta.general_health} value={form.health} onChange={set("health")} C={C} />
      <Field C={C} label="Height (cm)" value={form.height} onChangeText={set("height")} keyboardType="numeric" />
      <Field C={C} label="Weight (kg)" value={form.weight} onChangeText={set("weight")} keyboardType="numeric" />
      <Text style={{ color: C.text, fontWeight: "600", marginTop: 12, marginBottom: 6 }}>Household income group</Text>
      <Chips options={meta.income_groups} value={form.income} onChange={set("income")} C={C} />
      <Text style={{ color: C.text, fontWeight: "600", marginTop: 8, marginBottom: 6 }}>Poor physical health days (last 30)</Text>
      <Stepper value={form.phys} min={0} max={30} C={C} onChange={set("phys")} />
      <View style={{ marginTop: 10 }}>
        <Row label="Any exercise in the past month?" value={form.exercise} onChange={set("exercise")} C={C} />
        <Row label="Serious difficulty walking?" value={form.walk} onChange={set("walk")} C={C} />
        <Row label="Heart disease or heart attack?" value={form.heart} onChange={set("heart")} C={C} />
      </View>
      <Btn title="Calculate my risk" onPress={onCalculate} C={C} busy={busy} />
      <Muted C={C} style={{ textAlign: "center", marginTop: 10 }}>Screening aid only. Not a medical diagnosis.</Muted>
    </View>
  );
}

export function ResultView({ result, scenario, meta, C, onWhatIf, onBack, onSave, onShare, busy }) {
  const color = LEVEL[result.level] || C.teal;
  const maxAbs = Math.max(0.0001, ...(result.factors || []).map((f) => Math.abs(f.effect)));
  return (
    <View>
      <View style={[card(C), { alignItems: "center" }]}>
        <Muted C={C}>YOUR RISK LEVEL</Muted>
        <View style={{ backgroundColor: color, borderRadius: 20, paddingHorizontal: 18, paddingVertical: 6, marginVertical: 6 }}>
          <Text style={{ color: "#fff", fontWeight: "700", fontSize: 16 }}>{result.level}</Text>
        </View>
        <Text style={{ color: C.text, fontSize: 54, fontWeight: "800" }}>{result.risk_percent}%</Text>
        <Meter percent={result.risk_percent} meta={meta} C={C} />
        <Text style={{ color: C.muted, textAlign: "center" }}>About {Math.round(result.risk_percent)} in 100 people like you. That is {result.times_average}x the average adult ({result.average_adult_percent}%). BMI {result.bmi}.</Text>
        <Text style={{ color: C.text, textAlign: "center", marginTop: 10 }}>{result.advice}</Text>
        <View style={{ flexDirection: "row", marginTop: 4 }}>
          <View style={{ flex: 1, marginRight: 6 }}><Btn title="Save to history" onPress={onSave} C={C} ghost /></View>
          <View style={{ flex: 1, marginLeft: 6 }}><Btn title="Share" onPress={onShare} C={C} ghost /></View>
        </View>
      </View>

      <View style={card(C)}>
        <H C={C}>Why this result</H>
        <Muted C={C}>Orange raises your risk, teal lowers it.</Muted>
        {(result.factors || []).map((f) => (
          <View key={f.factor} style={{ marginBottom: 8 }}>
            <Text style={{ color: C.text, fontSize: 13 }}>{f.factor}</Text>
            <View style={{ height: 10, backgroundColor: C.border, borderRadius: 5, marginTop: 3 }}>
              <View style={{ height: 10, borderRadius: 5, width: Math.max(4, (Math.abs(f.effect) / maxAbs) * 100) + "%", backgroundColor: f.direction === "raises" ? CORAL : C.teal }} />
            </View>
          </View>
        ))}
      </View>

      <View style={card(C)}>
        <H C={C}>What-if lab</H>
        <Muted C={C}>Change your BMI or exercise and see the new risk.</Muted>
        <Text style={{ color: C.text, marginBottom: 6 }}>If my BMI were</Text>
        <Stepper value={scenario.bmi} min={15} max={50} C={C} onChange={(v) => onWhatIf({ ...scenario, bmi: v })} />
        <Row label="What if I exercised regularly?" value={scenario.exercise} C={C} onChange={(v) => onWhatIf({ ...scenario, exercise: v })} />
        {busy ? <ActivityIndicator color={C.teal} /> : null}
        {result.scenario ? (
          <View style={{ marginTop: 6 }}>
            <Text style={{ color: C.text, fontSize: 15 }}>
              Scenario risk: <Text style={{ fontWeight: "700" }}>{result.scenario.risk_percent}%</Text> ({result.scenario.level}),{" "}
              <Text style={{ color: result.scenario.change_points <= 0 ? "#16A34A" : "#DC2626", fontWeight: "700" }}>{result.scenario.change_points > 0 ? "+" : ""}{result.scenario.change_points} points</Text>
            </Text>
            <Muted C={C} style={{ marginTop: 4 }}>Survey patterns, not a promise for one person.</Muted>
          </View>
        ) : null}
      </View>

      <View style={card(C)}>
        <H C={C}>Healthy-habit tips</H>
        {(result.tips || []).map((t) => <Text key={t} style={{ color: C.text, marginBottom: 4 }}>{"\u2022"} {t}</Text>)}
      </View>
      <Muted C={C} style={{ textAlign: "center" }}>{result.disclaimer}</Muted>
      <Btn title="New assessment" onPress={onBack} C={C} />
      <View style={{ height: 20 }} />
    </View>
  );
}

export function ExploreView({ C, load, initial, busy }) {
  const [d, setD] = useState(initial || null);
  const run = async () => { const r = await load(); if (r) setD(r); };
  return (
    <View>
      <View style={card(C)}>
        <H C={C}>Explore your profile</H>
        <Muted C={C}>Uses the answers on the Check tab.</Muted>
        <Btn title={d ? "Refresh for my profile" : "Load for my profile"} onPress={run} C={C} busy={busy} />
      </View>
      {d ? (
        <View>
          <View style={card(C)}>
            <H C={C}>Age journey</H>
            <Muted C={C}>Estimated risk (%) if only your age changes.</Muted>
            <BarChart C={C} labels={d.age.labels.map((l) => l.slice(0, 2))} series={[{ values: d.age.you, color: CORAL }, { values: d.age.average, color: GREY }]} />
            <Legend C={C} items={[["Your profile", CORAL], ["Average adult", GREY]]} />
          </View>
          <View style={card(C)}>
            <H C={C}>People like you</H>
            <Text style={{ color: C.text }}>{d.peers.n.toLocaleString ? d.peers.n.toLocaleString() : d.peers.n} survey adults share your age group and health rating. <Text style={{ fontWeight: "700" }}>{d.peers.peer_percent}%</Text> of them have diabetes.</Text>
            <View style={{ height: 8 }} />
            <BarChart C={C} labels={["You (model)", "People like you", "All adults"]} series={[{ values: [d.peers.you_percent, d.peers.peer_percent, d.peers.overall_percent], color: C.teal }]} />
            <Muted C={C} style={{ marginTop: 6 }}>The model also uses BMI, income, exercise and more.</Muted>
          </View>
          <View style={card(C)}>
            <H C={C}>Risk across BMI</H>
            <Muted C={C}>Estimated risk (%) at each BMI, other answers unchanged. Your BMI: {d.curve.your_bmi}.</Muted>
            <BarChart C={C} labels={d.curve.bmi.map(String)} series={[{ values: d.curve.risk_percent, color: C.teal }]} />
          </View>
        </View>
      ) : null}
    </View>
  );
}

export function InsightsView({ C, data }) {
  if (!data) return <ActivityIndicator color={C.teal} style={{ marginTop: 30 }} />;
  return (
    <View>
      <View style={card(C)}>
        <H C={C}>The survey behind DiaScope</H>
        <Text style={{ color: C.text }}>{data.adults.toLocaleString ? data.adults.toLocaleString() : data.adults} adults, CDC BRFSS 2024. <Text style={{ fontWeight: "700" }}>{data.diabetes_percent}%</Text> have diabetes.</Text>
      </View>
      <View style={card(C)}>
        <H C={C}>Diabetes rate by age group (%)</H>
        <BarChart C={C} labels={data.age.labels.map((l) => l.slice(0, 2))} series={[{ values: data.age.rates, color: C.teal }]} />
      </View>
      <View style={card(C)}>
        <H C={C}>By self-rated general health (%)</H>
        <BarChart C={C} labels={["Exc", "V.good", "Good", "Fair", "Poor"]} series={[{ values: data.health.rates, color: CORAL }]} />
      </View>
      <View style={card(C)}>
        <H C={C}>By body mass index (%)</H>
        <BarChart C={C} labels={["<18", "18-25", "25-30", "30-35", "35-40", "40+"]} series={[{ values: data.bmi.rates, color: C.teal }]} />
      </View>
    </View>
  );
}

export function HistoryView({ C, items, onClear }) {
  if (!items) return <ActivityIndicator color={C.teal} style={{ marginTop: 30 }} />;
  if (!items.length) return <View style={card(C)}><H C={C}>My history</H><Text style={{ color: C.muted }}>Nothing saved yet. Tap "Save to history" on a result.</Text></View>;
  const last = items.slice(-12);
  return (
    <View>
      <View style={card(C)}>
        <H C={C}>Saved risk over time (%)</H>
        <BarChart C={C} labels={last.map((i) => i.date.slice(5, 10))} series={[{ values: last.map((i) => i.risk_percent), color: C.teal }]} />
      </View>
      <View style={card(C)}>
        <H C={C}>My history</H>
        <TRow C={C} head cells={["Date", "Risk %", "Level", "BMI"]} />
        {items.slice().reverse().map((i, k) => <TRow key={k} C={C} cells={[i.date.replace("T", " ").slice(0, 16), i.risk_percent, i.level, i.bmi]} />)}
        <Btn title="Clear my history" onPress={onClear} C={C} ghost />
      </View>
    </View>
  );
}

export function MoreView({ C, username, server, dark, setDark, onLogout, onChangeServer, model }) {
  return (
    <View>
      <View style={card(C)}>
        <H C={C}>Settings</H>
        <Text style={{ color: C.text }}>Signed in as <Text style={{ fontWeight: "700" }}>{username}</Text></Text>
        <Text style={{ color: C.muted, marginTop: 4 }}>Server: {server}</Text>
        <Row label="Dark mode" value={dark} onChange={setDark} C={C} />
        <Btn title="Change server" onPress={onChangeServer} C={C} ghost />
        <Btn title="Log out" onPress={onLogout} C={C} />
      </View>
      <View style={card(C)}>
        <H C={C}>Model information</H>
        {!model ? <ActivityIndicator color={C.teal} /> : (
          <View>
            <Muted C={C}>Model comparison (test set)</Muted>
            <TRow C={C} head cells={["Model", "ROC-AUC", "Recall@15%"]} />
            {model.comparison.map((r) => <TRow key={r.Model} C={C} cells={[r.Model, r["ROC-AUC"], r["Recall@0.15"]]} />)}
            <Muted C={C} style={{ marginTop: 10 }}>Alert line trade-off</Muted>
            <TRow C={C} head cells={["Threshold", "Recall", "Flagged %"]} />
            {model.thresholds.map((r) => <TRow key={r.Threshold} C={C} cells={[r.Threshold, r.Recall, r["% of people flagged"]]} />)}
            <Muted C={C} style={{ marginTop: 10 }}>Do the risk levels mean something?</Muted>
            <TRow C={C} head cells={["Level", "People", "Real rate %"]} />
            {model.risk_levels.map((r) => <TRow key={r["Risk level"]} C={C} cells={[r["Risk level"], r.People, r.Real_diabetes_rate]} />)}
          </View>
        )}
      </View>
      <View style={card(C)}>
        <H C={C}>Limitations</H>
        {((model && model.limitations) || []).map((t) => <Text key={t} style={{ color: C.text, marginBottom: 4 }}>{"\u2022"} {t}</Text>)}
        <Muted C={C} style={{ marginTop: 6 }}>DiaScope is a screening aid and not a medical diagnosis.</Muted>
      </View>
    </View>
  );
}

export function TabBar({ tab, setTab, C }) {
  const tabs = [["check", "Check", "\uD83E\uDE7A"], ["explore", "Explore", "\uD83D\uDD2D"], ["insights", "Insights", "\uD83D\uDCCA"], ["history", "History", "\uD83D\uDDC2"], ["more", "More", "\u2699"]];
  return (
    <View style={{ flexDirection: "row", backgroundColor: C.card, borderTopWidth: 1, borderTopColor: C.border, paddingBottom: Platform.OS === "ios" ? 18 : 6, paddingTop: 6 }}>
      {tabs.map(([k, t, icon]) => (
        <TouchableOpacity key={k} onPress={() => setTab(k)} style={{ flex: 1, alignItems: "center" }}>
          <Text style={{ fontSize: 18 }}>{icon}</Text>
          <Text style={{ fontSize: 11, color: tab === k ? C.teal : C.muted, fontWeight: tab === k ? "700" : "400" }}>{t}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------- app
export default function App() {
  const [dark, setDark] = useState(false);
  const C = dark ? DARK : LIGHT;
  const [accepted, setAccepted] = useState(false);
  const [server, setServer] = useState("http://192.168.1.115:8000");
  const [meta, setMeta] = useState(null);
  const [auth, setAuth] = useState(null);
  const [tab, setTab] = useState("check");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [result, setResult] = useState(null);
  const [scenario, setScenario] = useState({ bmi: 25, exercise: true });
  const [insights, setInsights] = useState(null);
  const [history, setHistory] = useState(null);
  const [model, setModel] = useState(null);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const say = (text, ok) => setNotice({ text, ok: !!ok });
  const base = () => server.trim().replace(/\/+$/, "");
  const fail = (e) => say(String(e.message || e).indexOf("Network request failed") >= 0 ? "Could not reach the server. Check the API is running, the Wi-Fi is the same and the address is right." : String(e.message || e));

  async function call(path, method, body) {
    const headers = { "Content-Type": "application/json" };
    if (auth) headers.Authorization = "Bearer " + auth.token;
    const r = await fetch(base() + path, { method: method || "GET", headers, body: body ? JSON.stringify(body) : undefined });
    let data = null;
    try { data = await r.json(); } catch (e) { data = null; }
    if (r.status === 401 && auth) { setAuth(null); throw new Error("Session expired. Please log in again."); }
    if (!r.ok) throw new Error(data && typeof data.detail === "string" ? data.detail : "Please check your entries (server said " + r.status + ").");
    return data;
  }

  const profile = (extra) => ({ age_group: form.age, general_health: form.health, height_cm: parseFloat(form.height), weight_kg: parseFloat(form.weight), income_group: form.income, poor_health_days: form.phys, exercise: form.exercise, difficulty_walking: form.walk, heart_disease: form.heart, ...extra });
  const invalid = () => { const h = parseFloat(form.height), w = parseFloat(form.weight); if (!(h >= 100 && h <= 230)) return "Height must be between 100 and 230 cm."; if (!(w >= 25 && w <= 300)) return "Weight must be between 25 and 300 kg."; return null; };
  const guard = async (fn) => { setBusy(true); setNotice(null); try { return await fn(); } catch (e) { fail(e); return null; } finally { setBusy(false); } };

  const connect = () => guard(async () => { const r = await fetch(base() + "/meta"); setMeta(await r.json()); });
  const login = (u, p) => guard(async () => { const r = await call("/login", "POST", { username: u, password: p }); setAuth({ token: r.token, username: r.username }); });
  const register = (u, p, p2, done) => guard(async () => {
    if (p !== p2) throw new Error("The two passwords do not match.");
    const r = await call("/register", "POST", { username: u, password: p });
    say(r.message, true); done();
  });
  const logout = () => { setAuth(null); setResult(null); setHistory(null); setTab("check"); setNotice(null); };
  const calculate = () => guard(async () => {
    const bad = invalid(); if (bad) throw new Error(bad);
    const res = await call("/predict", "POST", profile({}));
    setResult(res); setScenario({ bmi: Math.min(50, Math.max(15, Math.round(res.bmi))), exercise: form.exercise });
  });
  const whatIf = (next) => { setScenario(next); return guard(async () => setResult(await call("/predict", "POST", profile({ scenario_bmi: next.bmi, scenario_exercise: next.exercise })))); };
  const save = () => guard(async () => { const r = await call("/history", "POST", profile({})); say("Saved: " + r.risk_percent + "% (" + r.level + ")", true); setHistory(null); });
  const share = () => Share.share({ message: "DiaScope: my estimated diabetes risk is " + result.risk_percent + "% (" + result.level + "). Screening aid only, not a diagnosis." });
  const loadExplore = () => guard(async () => {
    const bad = invalid(); if (bad) throw new Error(bad);
    const [age, peers, curve] = await Promise.all([call("/age-journey", "POST", profile({})), call("/peers", "POST", profile({})), call("/bmi-curve", "POST", profile({}))]);
    return { age, peers, curve };
  });
  const clearHistory = () => guard(async () => { await call("/history", "DELETE"); setHistory([]); });

  useEffect(() => {
    if (!auth) return;
    if (tab === "insights" && !insights) call("/insights").then(setInsights).catch(fail);
    if (tab === "history") call("/history").then((d) => setHistory(d.items)).catch(fail);
    if (tab === "more" && !model) call("/model-info").then(setModel).catch(fail);
  }, [tab, auth]);

  let body;
  if (!accepted) body = <Welcome C={C} onAccept={() => setAccepted(true)} />;
  else if (!meta) body = <ConnectScreen C={C} server={server} setServer={setServer} onConnect={connect} busy={busy} />;
  else if (!auth) body = <AuthScreen C={C} onLogin={login} onRegister={register} busy={busy} />;
  else if (tab === "check") body = result ? <ResultView result={result} scenario={scenario} meta={meta} C={C} onWhatIf={whatIf} onBack={() => setResult(null)} onSave={save} onShare={share} busy={busy} /> : <FormView C={C} meta={meta} form={form} set={set} onCalculate={calculate} busy={busy} />;
  else if (tab === "explore") body = <ExploreView C={C} load={loadExplore} busy={busy} />;
  else if (tab === "insights") body = <InsightsView C={C} data={insights} />;
  else if (tab === "history") body = <HistoryView C={C} items={history} onClear={clearHistory} />;
  else body = <MoreView C={C} username={auth.username} server={server} dark={dark} setDark={setDark} onLogout={logout} onChangeServer={() => { logout(); setMeta(null); }} model={model} />;

  return (
    <View style={{ flex: 1, backgroundColor: C.bg, paddingTop: Platform.OS === "android" ? StatusBar.currentHeight : 44 }}>
      <StatusBar barStyle={dark ? "light-content" : "dark-content"} />
      <View style={{ backgroundColor: "#0F766E", paddingHorizontal: 18, paddingVertical: 12, flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <View>
          <Text style={{ color: "#fff", fontSize: 24, fontWeight: "800" }}>DiaScope</Text>
          <Text style={{ color: "#CFE8E4", fontSize: 12 }}>{auth ? "Signed in as " + auth.username : "Diabetes risk intelligence"}</Text>
        </View>
        <View style={{ alignItems: "center" }}>
          <Text style={{ color: "#CFE8E4", fontSize: 11 }}>Dark</Text>
          <Switch value={dark} onValueChange={setDark} />
        </View>
      </View>
      {notice ? (
        <TouchableOpacity onPress={() => setNotice(null)} style={{ backgroundColor: notice.ok ? "#DCFCE7" : "#FEE2E2", padding: 10 }}>
          <Text style={{ color: notice.ok ? "#166534" : "#991B1B" }}>{notice.text}</Text>
        </TouchableOpacity>
      ) : null}
      <ScrollView style={{ padding: 16 }} keyboardShouldPersistTaps="handled">{body}</ScrollView>
      {auth ? <TabBar tab={tab} setTab={setTab} C={C} /> : null}
    </View>
  );
}
