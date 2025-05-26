select ws.*, avg(v.value) from devices_measurement as m
inner join api_location l on l.id = m.location_id
inner join devices_values v on v.measurement_id = m.id
inner join workshops_workshopspot ws on ST_Within(l.coordinates, ws.area) and ws.workshop_id = m.workshop_id
where m.workshop_id = 'x' and v.dimension = 7 -- temperature
group by ws.*;

CREATE INDEX idx_spot_area
ON workshops_workshopspot
USING GIST (area);

CREATE INDEX idx_location_coordinates
ON api_location
USING GIST (coordinates);

CREATE INDEX idx_spot_area_workshop_id
ON workshops_workshopspot
USING GIST (area, workshop_id);

CREATE INDEX idx_values_measurement_id
ON devices_values (measurement_id);

CREATE INDEX idx_measurement_workshop_id
ON devices_measurement (workshop_id);

CREATE INDEX idx_values_dimension
ON devices_values (dimension);