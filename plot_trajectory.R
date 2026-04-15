# Plot GNSS trajectory on interactive map
library(leaflet)
library(readr)
library(dplyr)
library(sf)

# Read the solution file, skipping header comments
solution <- read_delim(
  "out/solution_first.pos",
  delim = " ",
  skip = 10,
  col_names = c("date", "time", "lat", "lon", "height", "Q", "ns", 
                "sdn", "sde", "sdu", "sdne", "sdeu", "sdun", "age", "ratio"),
  col_types = cols(.default = col_double(), date = col_character(), time = col_character())
)

# Combine date and time, remove rows with any NA values
solution <- solution %>%
  filter(!is.na(lat) & !is.na(lon)) %>%
  mutate(
    datetime = paste(date, time),
    quality_label = case_when(
      Q == 1 ~ "Fix",
      Q == 2 ~ "Float",
      Q == 4 ~ "DGPS",
      Q == 5 ~ "Single",
      TRUE ~ "Other"
    )
  )

# Print summary
cat("Trajectory Summary:\n")
cat("Time range:", min(solution$datetime), "to", max(solution$datetime), "\n")
cat("Points:", nrow(solution), "\n")
cat("Lat range:", min(solution$lat), "to", max(solution$lat), "\n")
cat("Lon range:", min(solution$lon), "to", max(solution$lon), "\n")
cat("Height range:", round(min(solution$height), 1), "to", round(max(solution$height), 1), "m\n")
cat("Mean horizontal accuracy (sdn):", round(mean(solution$sdn), 2), "m\n")
cat("Mean horizontal accuracy (sde):", round(mean(solution$sde), 2), "m\n\n")

# Create map
map <- leaflet(data = solution) %>%
  addTiles(urlTemplate = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png") %>%
  
  # Add trajectory line
  addPolylines(
    lng = ~lon, lat = ~lat,
    color = "blue", weight = 2, opacity = 0.7,
    popup = ~paste("Time:", datetime, "<br>Height:", round(height, 1), "m<br>Acc:", round(sdn, 2), "m")
  ) %>%
  
  # Add start point (green)
  addCircles(
    data = solution[1,],
    lng = ~lon, lat = ~lat,
    radius = 5, color = "green", weight = 2, opacity = 0.8,
    popup = "START: 05:40:23"
  ) %>%
  
  # Add end point (red)
  addCircles(
    data = solution[nrow(solution),],
    lng = ~lon, lat = ~lat,
    radius = 5, color = "red", weight = 2, opacity = 0.8,
    popup = "END: 05:46:55"
  ) %>%
  
  # Add all waypoints with color coding by accuracy
  addCircleMarkers(
    lng = ~lon, lat = ~lat,
    radius = 3,
    color = ifelse(solution$sdn < 1, "darkgreen", "orange"),
    opacity = 0.6,
    popup = ~paste(
      "Time:", datetime, "<br>",
      "Pos:", round(lat, 6), ",", round(lon, 6), "<br>",
      "Height:", round(height, 1), "m<br>",
      "Horiz Acc:", round(sdn, 2), "m<br>",
      "Quality:", quality_label
    )
  ) %>%
  
  setView(lng = mean(solution$lon), lat = mean(solution$lat), zoom = 16)

# Save map
htmlwidgets::saveWidget(map, "trajectory_map.html")
cat("✓ Interactive map saved to: trajectory_map.html\n")
cat("  Open in browser to view trajectory\n")

# Also create a simple CSV export
export_df <- solution %>%
  select(datetime, lat, lon, height, Q, quality_label, sdn, sde) %>%
  rename(
    timestamp = datetime,
    latitude = lat,
    longitude = lon,
    elevation_m = height,
    quality_code = Q,
    quality_type = quality_label,
    horiz_acc_n = sdn,
    horiz_acc_e = sde
  )

write_csv(export_df, "trajectory_corrected.csv")
cat("✓ CSV export saved to: trajectory_corrected.csv\n\n")

# Print first few rows
cat("First 5 epochs:\n")
print(head(export_df, 5))
