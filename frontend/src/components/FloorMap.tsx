"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { Layers2, Minus, Plus, ScanLine } from "lucide-react";

import type { RouteMapNode } from "@/lib/api";

interface FloorMapProps {
  nodes: RouteMapNode[];
  activeStep: number;
}

const VIEW_WIDTH = 1000;
const VIEW_HEIGHT = 500;
const MAP_PADDING = 100;

export function FloorMap({ nodes, activeStep }: FloorMapProps) {
  const floors = [...new Map(nodes.map((node) => [node.floor, node.floor_name])).entries()]
    .sort(([first], [second]) => first - second);
  const [activeFloor, setActiveFloor] = useState<number | null>(null);
  const [zoom, setZoom] = useState(1);
  const selectedFloor = activeFloor ?? floors[0]?.[0] ?? 0;
  const floorNodes = nodes.filter((node) => node.floor === selectedFloor);
  useEffect(() => {
    const activeNode = nodes[Math.min(activeStep, nodes.length - 1)];
    if (activeNode) setActiveFloor(activeNode.floor);
  }, [activeStep, nodes]);

  const plottedNodes = useMemo(() => {
    if (!nodes.length) return [];
    const minX = Math.min(...nodes.map((node) => node.x));
    const maxX = Math.max(...nodes.map((node) => node.x));
    return nodes.map((node) => ({
      ...node,
      px: MAP_PADDING + ((node.x - minX) / (maxX - minX || 1)) * (VIEW_WIDTH - MAP_PADDING * 2),
      py: node.floor === Math.min(...nodes.map((place) => place.floor)) ? 212 : 286,
    }));
  }, [nodes]);
  const visibleRouteNodes = plottedNodes.filter((node) => node.floor === selectedFloor);
  const routeLine = visibleRouteNodes.map((node) => `${node.px},${node.py}`).join(" ");
  const focusedNode = plottedNodes[Math.min(activeStep, Math.max(plottedNodes.length - 1, 0))];
  const floorName = floors.find(([floor]) => floor === selectedFloor)?.[1];

  return (
    <section className="map-panel" aria-label="Interactive campus floor map">
      <div className="map-toolbar">
        <div className="map-toolbar-title">
          <span className="map-symbol"><Layers2 aria-hidden="true" size={17} /></span>
          <div><strong>Campus map</strong><small>{floorNodes.length ? `${floorNodes.length} route stops on this floor` : "Select a route to view the map"}</small></div>
        </div>
        <div className="map-controls">
          <button aria-label="Zoom out" className="icon-button" onClick={() => setZoom((value) => Math.max(.8, value - .1))} type="button"><Minus size={16} /></button>
          <span className="zoom-value">{Math.round(zoom * 100)}%</span>
          <button aria-label="Zoom in" className="icon-button" onClick={() => setZoom((value) => Math.min(1.3, value + .1))} type="button"><Plus size={16} /></button>
          <button aria-label="Reset map zoom" className="icon-button map-reset" onClick={() => setZoom(1)} type="button"><ScanLine size={16} /></button>
        </div>
      </div>
      <div className="map-canvas" style={{ "--map-zoom": zoom } as CSSProperties}>
        <div className="map-content">
          <div className="map-grid" />
          <div className="map-orientation"><span>N</span><i /></div>
          <div className="map-building-label">NORTH WING <span>·</span> {floorName?.toUpperCase() ?? "SELECT A FLOOR"}</div>
          <div className="map-room room-one"><span>ATRIUM</span><small>OPEN STUDY</small></div>
          <div className="map-room room-two"><span>LAB 103</span><small>RESEARCH</small></div>
          <div className="map-room room-three"><span>LAB 102</span><small>TEACHING</small></div>
          <div className="map-corridor corridor-horizontal" />
          <div className="map-corridor corridor-vertical corridor-vertical-one" />
          <div className="map-corridor corridor-vertical corridor-vertical-two" />
          {visibleRouteNodes.length > 0 && (
            <svg className="route-overlay" viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`} preserveAspectRatio="none" aria-hidden="true">
              <polyline className="route-shadow" points={routeLine} />
              <polyline className="route-stroke" points={routeLine} />
              {visibleRouteNodes.map((node) => <circle className="route-halo" key={`halo-${node.place_id}`} cx={node.px} cy={node.py} r="15" />)}
            </svg>
          )}
          {visibleRouteNodes.map((node, index) => {
            const focused = focusedNode?.place_id === node.place_id;
            const start = nodes[0]?.place_id === node.place_id;
            const destination = nodes.at(-1)?.place_id === node.place_id;
            return (
              <div
                className={`map-stop ${focused ? "map-stop--focused" : ""} ${destination ? "map-stop--destination" : ""} ${index % 2 ? "map-stop--label-above" : ""}`}
                key={node.place_id}
                style={{ left: `${(node.px / VIEW_WIDTH) * 100}%`, top: `${(node.py / VIEW_HEIGHT) * 100}%` }}
                title={`${node.name} · ${node.floor_name}`}
              >
                <span className="map-stop-dot">{start ? "S" : ""}</span>
                <span className="map-stop-label">{node.name}</span>
              </div>
            );
          })}
          <div className="map-scale"><i /> 10 m</div>
        </div>
        {focusedNode && focusedNode.floor !== selectedFloor && <div className="map-floor-hint"><Layers2 size={15} /> Current step is on {focusedNode.floor_name}</div>}
      </div>
      <div className="floor-tabs" role="tablist" aria-label="Select floor">
        {floors.map(([floor, name]) => (
          <button aria-selected={selectedFloor === floor} className={`floor-tab ${selectedFloor === floor ? "floor-tab--active" : ""}`} key={floor} onClick={() => setActiveFloor(floor)} role="tab" type="button">
            <span className="floor-tab-mark" />{name}<span className="floor-tab-count">{nodes.filter((node) => node.floor === floor).length}</span>
          </button>
        ))}
        <span className="map-key"><i /> Your route</span>
      </div>
    </section>
  );
}
