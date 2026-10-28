"use client";

import { useEffect, useState } from "react";
import {
  ArrowDownUp, ArrowRight, Building2, Check, ChevronRight, Clock3,
  Compass, Footprints, LocateFixed, MoveVertical, Navigation, Route as RouteIcon,
  Sparkles, X,
} from "lucide-react";

import { FloorMap } from "@/components/FloorMap";
import { PlacePicker } from "@/components/PlacePicker";
import { SignVerification } from "@/components/SignVerification";
import { checkApi, fetchRoute, type RouteResponse, type SearchMatch } from "@/lib/api";

const initialStart: SearchMatch = {
  place_id: "GATE", name: "Gate", category: "entrance", department: "",
  floor: 0, floor_name: "Ground Floor", score: 100,
};
const initialDestination: SearchMatch = {
  place_id: "LAB101", name: "Lab 101", category: "laboratory", department: "Physics",
  floor: 1, floor_name: "First Floor", score: 100,
};

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return minutes ? `${minutes} min ${remaining} sec` : `${remaining} sec`;
}

function stepIcon(instruction: string) {
  if (/stairs|staircase/i.test(instruction)) return <MoveVertical size={17} />;
  if (/lift|elevator/i.test(instruction)) return <Building2 size={17} />;
  if (/start at/i.test(instruction)) return <LocateFixed size={17} />;
  return <Footprints size={17} />;
}

export default function HomePage() {
  const [start, setStart] = useState<SearchMatch | null>(initialStart);
  const [destination, setDestination] = useState<SearchMatch | null>(initialDestination);
  const [route, setRoute] = useState<RouteResponse | null>(null);
  const [routeError, setRouteError] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [requestNumber, setRequestNumber] = useState(0);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    checkApi(controller.signal)
      .then(() => setApiOnline(true))
      .catch(() => { if (!controller.signal.aborted) setApiOnline(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!start || !destination) {
      setRoute(null);
      setRouteError("");
      return;
    }
    const controller = new AbortController();
    let current = true;
    setLoading(true);
    setRouteError("");
    fetchRoute(start.place_id, destination.place_id, controller.signal)
      .then((result) => {
        if (!current) return;
        setRoute(result);
        setActiveStep(0);
      })
      .catch((error: unknown) => {
        if (!current || controller.signal.aborted) return;
        setRoute(null);
        setRouteError(error instanceof Error ? error.message : "Unable to calculate this route.");
      })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; controller.abort(); };
  }, [start, destination, requestNumber]);

  const instructions = route?.instructions ?? [];
  const activeInstruction = instructions[activeStep] ?? "Choose start and destination points to see directions.";

  return (
    <main className="app-shell" id="top">
      <header className="topbar">
        <a aria-label="Wayfind Campus home" className="brand-lockup" href="#top">
          <span className="brand-symbol"><Compass size={21} /></span>
          <span className="brand-name">way<span>find</span><sup>campus</sup></span>
        </a>
        <div className="topbar-center"><span className="topbar-dot" /> INDOOR NAVIGATION <span className="topbar-divider">/</span> NORTH CAMPUS</div>
        <div className="topbar-right">
          <span className={`api-status ${apiOnline === false ? "api-status--offline" : ""}`}>
            <i /> {apiOnline === null ? "CHECKING API" : apiOnline ? "API CONNECTED" : "API OFFLINE"}
          </span>
          <span className="profile-chip">NC</span>
        </div>
      </header>

      <div className="workspace">
        <aside className="planner-column">
          <div className="page-heading">
            <div className="heading-meta"><span className="heading-index">01</span><span>PLAN YOUR WALK</span></div>
            <h1>Find your<br /><em>way around.</em></h1>
            <p>Indoor directions across North Campus, floor by floor.</p>
          </div>

          <section aria-label="Route planner" className="planner-panel">
            <div className="panel-heading">
              <div><span className="eyebrow">ROUTE PLANNER</span><h2>Where to?</h2></div>
              <span className="planner-icon"><RouteIcon size={17} /></span>
            </div>
            <div className="route-fields">
              <div aria-hidden="true" className="route-rail"><i /><span /><i /></div>
              <PlacePicker label="STARTING POINT" value={start} placeholder="Search a place or room" onSelect={setStart} />
              <PlacePicker label="DESTINATION" value={destination} placeholder="Where are you going?" onSelect={setDestination} />
              <button aria-label="Swap start and destination" className="swap-button" onClick={() => { setStart(destination); setDestination(start); }} type="button"><ArrowDownUp size={15} /></button>
            </div>
            <div className="planner-footer">
              <span><Sparkles size={14} /> Fuzzy search enabled</span>
              <button className="build-route-button" disabled={!start || !destination || loading} onClick={() => setRequestNumber((number) => number + 1)} type="button">
                {loading ? "Finding route" : "Show route"}<ArrowRight size={16} />
              </button>
            </div>
          </section>

          <div className="route-summary-row">
            <div className="summary-cell"><span className="summary-icon summary-icon--green"><Footprints size={16} /></span><div><small>DISTANCE</small><strong>{route ? <>{route.total_distance_m.toFixed(1)} <i>m</i></> : "—"}</strong></div></div>
            <div className="summary-separator" />
            <div className="summary-cell"><span className="summary-icon summary-icon--lime"><Clock3 size={16} /></span><div><small>WALKING TIME</small><strong>{route ? formatDuration(route.estimated_walking_time_seconds) : "—"}</strong></div></div>
          </div>

          {routeError && <div className="route-error" role="alert"><X size={15} />{routeError}</div>}

          <section aria-labelledby="directions-title" className="directions-section">
            <div className="section-heading">
              <div><span className="eyebrow">YOUR JOURNEY</span><h2 id="directions-title">Step-by-step</h2></div>
              {route && <span className="step-count">{instructions.length} STEPS</span>}
            </div>
            {loading && <div className="directions-loading"><span className="loading-pulse" /> Calculating the best route…</div>}
            {!loading && route && (
              <ol className="directions-list">
                {instructions.map((instruction, index) => {
                  const selected = index === activeStep;
                  const last = index === instructions.length - 1;
                  return (
                    <li className={`direction-item ${selected ? "direction-item--active" : ""}`} key={`${index}-${instruction}`}>
                      <button aria-current={selected ? "step" : undefined} className="direction-button" onClick={() => setActiveStep(index)} type="button">
                        <span className={`direction-icon ${selected ? "direction-icon--active" : ""} ${last ? "direction-icon--finish" : ""}`}>{last ? <Check size={16} /> : stepIcon(instruction)}</span>
                        <span className="direction-copy"><span>{instruction}</span>{route.map_nodes[index] && <small>{route.map_nodes[index].floor_name}</small>}</span>
                        <ChevronRight className="direction-chevron" size={15} />
                      </button>
                    </li>
                  );
                })}
              </ol>
            )}
            {!loading && !route && !routeError && <div className="directions-empty"><span><Navigation size={19} /></span><p>Your route will appear here, with every floor transition called out.</p></div>}
            {route && <div className="route-endpoints"><span className="endpoint-dot endpoint-dot--start" /><span>{route.map_nodes[0]?.name}</span><span className="endpoint-line" /><span className="endpoint-dot endpoint-dot--end" /><strong>{route.map_nodes.at(-1)?.name}</strong></div>}
          </section>

          <SignVerification destination={destination} />
        </aside>

        <section aria-label="Route map and current instruction" className="map-column">
          <div className="map-context-bar">
            <div className="map-context-location"><span className="context-pin"><Building2 size={16} /></span><div><strong>North Campus</strong><small>Building A · Indoor map</small></div></div>
            <div className="map-live-status"><span /> LIVE ROUTE</div>
          </div>
          <FloorMap activeStep={activeStep} nodes={route?.map_nodes ?? []} />
          <div className="next-step-banner">
            <div className="next-step-marker"><Navigation size={17} /></div>
            <div className="next-step-copy"><span>NEXT INSTRUCTION <i>·</i> STEP {route ? Math.min(activeStep + 1, instructions.length) : 0} OF {instructions.length}</span><strong>{activeInstruction}</strong></div>
            <div className="step-controls">
              <button aria-label="Previous instruction" disabled={!route || activeStep <= 0} onClick={() => setActiveStep((step) => Math.max(0, step - 1))} type="button"><ArrowRight className="arrow-previous" size={17} /></button>
              <button aria-label="Next instruction" disabled={!route || activeStep >= instructions.length - 1} onClick={() => setActiveStep((step) => Math.min(instructions.length - 1, step + 1))} type="button"><ArrowRight size={17} /></button>
            </div>
          </div>
          <div className="map-footer"><span><i /> MAP DATA · NORTH CAMPUS</span><span>Route recalculates when locations change</span></div>
        </section>
      </div>

      <footer className="app-footer"><span>WAYFIND CAMPUS <i>©</i> 2026</span><span>Accessibility-first routing <b>·</b> Indoor navigation</span></footer>
    </main>
  );
}
