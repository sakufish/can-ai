import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import * as topojson from "topojson-client";
import "./home.css";

const Home: React.FC = () => {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const [paused, setPaused] = useState(false);
  const initialScale = window.innerHeight / 2.3;

  useEffect(() => {
    const width = window.innerWidth;
    const height = window.innerHeight;

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .style("background", "#000");

    const projection = d3.geoOrthographic()
      .scale(initialScale)
      .translate([width / 2, height / 2])
      .rotate([-33.5, -1]);

    const path = d3.geoPath(projection);
    const color = d3.scaleSequential(d3.interpolateYlGnBu).domain([-0.1, 2.0]);

    const g = svg.append("g");

    const globeCircle = g.append("circle")
      .attr("fill", "#0e1a2b")
      .attr("stroke", "#555")
      .attr("cx", width / 2)
      .attr("cy", height / 2)
      .attr("r", projection.scale());

    let land: d3.Selection<SVGPathElement, any, any, any>;
    let points: d3.Selection<SVGCircleElement, any, any, any>;
    let dataCentroid: [number, number] = [0, 0];

    Promise.all([
      d3.json("https://unpkg.com/world-atlas@2.0.2/countries-110m.json"),
      d3.json("/kenya_water_equity.json")
    ]).then(([worldData, equityData]) => {
      const world = worldData as any;
      const data = equityData as { lat: number; lon: number; score: number }[];

      const countries = topojson.feature(world, world.objects.countries);

      const avgLat = d3.mean(data, d => d.lat) ?? 0;
      const avgLon = d3.mean(data, d => d.lon) ?? 0;
      dataCentroid = [avgLon, avgLat];

      land = g.selectAll("path")
        .data(countries.features)
        .enter().append("path")
        .attr("fill", "#1e3d59")
        .attr("stroke", "#888")
        .attr("stroke-width", 0.3)
        .attr("d", path);

      points = g.selectAll("circle.data-point")
        .data(data)
        .enter().append("circle")
        .attr("class", "data-point")
        .attr("r", 0)
        .attr("fill", d => color(d.score))
        .attr("stroke", "#fff")
        .attr("stroke-width", 0.2)
        .attr("opacity", 0)
        .on("mouseover", (event, d) => {
          if (tooltipRef.current) {
            tooltipRef.current.style.display = "block";
            tooltipRef.current.style.left = `${event.pageX + 10}px`;
            tooltipRef.current.style.top = `${event.pageY - 10}px`;
            tooltipRef.current.innerHTML =
              `Lat: ${d.lat.toFixed(2)}, Lon: ${d.lon.toFixed(2)}<br>Score: ${d.score.toFixed(2)}`;
          }
        })
        .on("mouseout", () => {
          if (tooltipRef.current) tooltipRef.current.style.display = "none";
        });

      const update = () => {
        land.attr("d", path);
        points
          .attr("cx", d => projection([d.lon, d.lat])[0])
          .attr("cy", d => projection([d.lon, d.lat])[1]);
      };

      const animatePoints = () => {
        points.transition()
          .delay((_, i) => i * 3)
          .duration(800)
          .attr("r", 3)
          .attr("opacity", 1);
      };

      svg.call(d3.drag()
        .on("start", () => setPaused(true))
        .on("drag", event => {
          const rotate = projection.rotate();
          const k = 0.25;
          projection.rotate([rotate[0] + event.dx * k, rotate[1] - event.dy * k]);
          update();
        })
        .on("end", () => setPaused(false)));

      update();
      animatePoints();

      // --- Zoom to Data ---
      (window as any).zoomToData = () => {
        if (!land || !points) return;

        setPaused(true);
        const targetScale = initialScale * 6;

        const currentRotate = projection.rotate();
        const targetRotate: [number, number, number] = [-dataCentroid[0], -dataCentroid[1], 0];

        d3.transition()
          .duration(2000)
          .tween("zoom", () => {
            const sInterp = d3.interpolate(projection.scale(), targetScale);
            const rInterp = d3.interpolateArray(currentRotate, targetRotate);

            return t => {
              projection
                .scale(sInterp(t))
                .rotate(rInterp(t));

              globeCircle.attr("r", projection.scale());

              land.attr("d", path);
              points
                .attr("cx", d => projection([d.lon, d.lat])[0])
                .attr("cy", d => projection([d.lon, d.lat])[1]);
            };
          });
      };

      // --- Reset Zoom ---
      (window as any).resetZoom = () => {
        const currentRotate = projection.rotate();
        const defaultRotate: [number, number, number] = [-33.5, -1, 0];

        d3.transition()
          .duration(1500)
          .tween("zoom", () => {
            const sInterp = d3.interpolate(projection.scale(), initialScale);
            const rInterp = d3.interpolateArray(currentRotate, defaultRotate);

            return t => {
              projection
                .scale(sInterp(t))
                .rotate(rInterp(t));

              globeCircle.attr("r", projection.scale());

              land.attr("d", path).attr("fill", "#1e3d59");
              points
                .attr("cx", d => projection([d.lon, d.lat])[0])
                .attr("cy", d => projection([d.lon, d.lat])[1])
                .attr("r", 3)
                .attr("opacity", 1);
            };
          })
          .on("end", () => setPaused(false));
      };
    });
  }, [paused]);

  return (
    <div className="home-container">
      <div className="controls">
        <button className="btn" onClick={() => (window as any).zoomToData()}>
          Zoom to Data
        </button>
        <button className="btn" onClick={() => (window as any).resetZoom()}>
          Reset View
        </button>
      </div>
      <div ref={tooltipRef} className="tooltip" />
      <svg ref={svgRef}></svg>
    </div>
  );
};

export default Home;
