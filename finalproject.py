""" 
Name: Luiz Gustavo Bernardes
CS230: Section 2
Data: Blue Bikes

URL: 

Description: This program uses a variety of metrics from Boston's Blue Bike data from September 2020 to answer a ton of questions that I had about how the entire system works. 
I created a sidebar where the user could customize the bike station or stations they would like to analyze. Once the user selects what stations they want to observe, graphs 
and other visuals come up to explain the data I was given. Some examples of data that could be seen are the busiest days of the week at each of the stations
and a map of the different trips that riders went on. 

References:
BlueBikes : https://bluebikes.com/system-data
Classroom Videos
Claude AI
MapBox : https://docs.mapbox.com/api/maps/styles/#mapbox-styles
Streamlit: https://streamlit.io/
BlueBikes Icon : https://bluebikes.com/how-it-works/meet-the-bike

"""

import streamlit as st
import pandas as pd 
import matplotlib.pyplot as plt
import pydeck as pdk


# Reading the bike data
def data_processing ():
   return pd.read_csv("202009-bluebikes-tripdata.csv").set_index("start station id")

#[FUNC2P]
def data_filter(star_stations, min_duration = 300):
    #[FUNCCALL2]
    df = data_processing()
    #[FILTER1]
    df = df.loc[df['start station name'].isin(star_stations)]
    #[FILTER2]
    df = df.loc[df['tripduration'] > min_duration]

    return df 
    
# Count the different bike stations
def count_stations(stations, df):
    #[LISTCOMP]
    station_list = [df.loc[df['start station name'].isin([station])].shape[0] for station in stations]
    return station_list

#[FUNCRETURN2]
def get_stats(df):
    clean = df[df["tripduration"] < 86400]
    return clean["tripduration"].max(), clean["tripduration"].min()

def all_stations():
    #[FUNCCALL2]
    df = data_processing()
    bike_list = []
    #[ITERLOOP]
    for ind, row in df.iterrows():
        if row['start station name'] not in bike_list:
            bike_list.append(row['start station name'])
    return bike_list

# Map of common trips
def generate_map(df):
    #[COLUMNS]
    df["trip_minutes"] = (df["tripduration"] / 60).round(2)
    trip_routes = (df.groupby(["start station name", "start station latitude", "start station longitude", "end station name",   "end station latitude",  "end station longitude"])
    .size()
    .reset_index(name="trip_count")
    #[SORT]
    .sort_values("trip_count", ascending=False))
    trip_routes = trip_routes[trip_routes["trip_count"] >= 1]
    if trip_routes.empty:
        st.warning("Not enough trip data to draw routes for the selected stations.")
        return
    trip_routes = trip_routes.rename(columns={
        "start station latitude":  "start_lat",
        "start station longitude": "start_lon",
        "end station latitude":    "end_lat",
        "end station longitude":   "end_lon",
        "start station name":      "start_name",
        "end station name":        "end_name",
    })

    #Line layer 
    arc_layer = pdk.Layer(
        "ArcLayer",
        data=trip_routes,
        get_source_position=["start_lon", "start_lat"],
        get_target_position=["end_lon",   "end_lat"],
        get_source_color=[50, 120, 255, 60],   
        get_width= "trip_count",  # thicker line = more trips
        width_scale = 1,
        width_min_pixels = 1,
        width_max_pixels = 8,
        pickable=True,
        auto_highlight=True,
    )

    #Iconlayer to show bike on station
    ICON_URL = "https://i.imgur.com/lVzigO7.png"
    icon_data = {
        "url": ICON_URL,
        "width": 120,
        "height": 120,
        "anchorY": 120
    }

    trip_routes["icon_data"] = [icon_data] * len(trip_routes)

    icon_layer = pdk.Layer(
        "IconLayer",
        data=trip_routes,
        get_position=["start_lon", "start_lat"],
        get_icon = 'icon_data',
        get_size = 4,
        size_scale=15,
        pickable=True,
    )
    
    lat = trip_routes["start_lat"].mean()
    lon = trip_routes["start_lon"].mean() #Helps center
    
    view_state = pdk.ViewState(
        latitude=lat,
        longitude= lon,
        zoom=14,
        pitch=0
        )
    
    tooltip = {
        "html": """
            <b>From:</b> {start_name}<br/>
            <b>To:</b> {end_name}<br/>
            <b>Trips:</b> {trip_count}
        """,
        "style": {"backgroundColor": "steelblue", "color": "white", "fontSize": "12px"}}

    map = pdk.Deck(
        layers=[arc_layer, icon_layer],
        initial_view_state= view_state,
        tooltip=tooltip,
        map_style= "dark",)

    st.subheader("Trip Routes Data")
    st.write("Number of routes:", len(trip_routes))
    display_df = trip_routes[["start_name", "end_name", "trip_count"]].reset_index(drop=True)
    st.dataframe(display_df, use_container_width=True)
    st.pydeck_chart(map)
    st.markdown("<p style='font-size: 11px; color: gray;'>Bike icon sourced from <a href='https://bluebikes.com/how-it-works/meet-the-bike' target='_blank'>Blue Bikes</a></p>", unsafe_allow_html=True)




# Line chart for days of the week in the stations
def line_chart(df, star_stations):
    df["day_of_week"] = pd.to_datetime(df["starttime"]).dt.day_name()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    filtered = df[df["start station name"].isin(star_stations)]
    pivot = filtered.groupby(["start station name", "day_of_week"]).size().reset_index(name="trip_count")
    
    dffig, dfaxis = plt.subplots(figsize=(10, 5))
    for station in star_stations:
        station_data = pivot[pivot["start station name"] == station]
        station_data = station_data.set_index("day_of_week").reindex(days).fillna(0).reset_index()

        dfaxis.plot(
            station_data["day_of_week"],
            station_data["trip_count"],
            marker="^",          # dot on each data point
            label=station[:20],  # truncate long names in legend
            linewidth=2,
        )
    dfaxis.set_title("Busiest Days of the Week by Station", fontsize=14, fontweight="bold")
    dfaxis.set_xlabel("Day of the Week", fontsize=11)
    dfaxis.set_ylabel("Number of Trips", fontsize=11)
    dfaxis.legend(fontsize=7, loc="upper right")
    dfaxis.grid(True, linestyle="--", alpha=0.5)
    plt.xticks(rotation=25)
    plt.tight_layout()

    return dffig



# Stations Pie chart
def pie_chart(counts, star_stations):
    plt.figure()
    plt.pie(counts, labels= star_stations, autopct= "%.2f%%")
    plt.title(f"The Breakdown of Stations")
    return plt



def main():
# Page Title
    st.title("Boston Blue Bikes Data App")
    st.write("Come explore the city of Boston by using the BlueBikes System. This app uses data from September 2020, to demonstrate how widespread the use of these bikes are " \
    "and how they are a great way to explore the city!")
    st.write("Open the sidebar to customize your experience!")
    #[ST3] An Image
    st.image("Boston Night Image.jpg")
    
    #Multi select widget and Sidebar
    #[ST1] and #[ST2]
    st.sidebar.write("Please select one of the options to analyze")
    star_stations = st.sidebar.multiselect("Select the station you would like to observe:", all_stations())
    min_duration = st.sidebar.slider("Minimum trip duration (minutes): ", 1, 300, 5)
    min_duration_sec = min_duration * 60

    st.sidebar.divider()
    user_filter = st.sidebar.radio(
    "Filter by rider type:",
    options=["All Riders", "Subscriber", "Customer"]
    )

    #[DICTMETHOD]
    users = {"Subscriber": "Monthly Member", "Customer": "Casual Rider"}
    st.sidebar.write("Selected type:", users.get(user_filter, "All"))

    if not star_stations:
        st.warning("Please select at least one station from the sidebar.")
        return

    data = data_filter(star_stations, min_duration_sec)
    if data.empty:
        st.warning("No trips able to analyze. Change slider to find trips.")
        return
    
    if user_filter != "All Riders":
        data = data[data["usertype"] == user_filter]
        if data.empty:
            st.warning(f"No {user_filter} trips found for these stations.")
            return

    #[LAMBDA]
    trip_min = lambda s: round(s / 60, 2)

    #[MAXMIN]
    max_trip, min_trip = get_stats(data)
    st.write("Longest trip:", trip_min(max_trip), "minutes")
    st.write("Shortest trip:", trip_min(min_trip), "minutes")
   
    counts = count_stations(star_stations, data)

    # Stations Pie chart and #[CHART1] 
    plt.title(f"The Breakdown of Stations")
    st.pyplot(pie_chart(counts, star_stations))
    st.divider()

    # Stations Line Chart and #[CHART2] 
    st.header("Busiest Days of the Week by Station")
    st.pyplot(line_chart(data, star_stations))
    st.divider()

    #[MAP]
    st.header("Map of Common Trips on Blue Bikes")
    generate_map(data)
main()
