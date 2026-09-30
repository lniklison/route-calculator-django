# Route Fuel Planning

This context describes road trips and fuel plans produced from the supplied truck-stop price data.

## Language

**Trip**:
A road journey from a free-form origin to a free-form destination within the contiguous United States.
_Avoid_: Route request, journey request

**Route**:
The drivable path and distance for a Trip, represented as GeoJSON.
_Avoid_: Map

**Fuel Station**:
A physical truck stop identified by its OPIS Truckstop ID. When the source contains several prices for the same station, its effective price is the lowest reported value.
_Avoid_: Gas point, fuel point

**Fuel Price**:
The supplied Retail Price interpreted as US dollars per gallon and normalized to three decimal places. Its fuel grade and effective date are unknown.
_Avoid_: Current price, live price

**Fuel Plan**:
An ordered set of Fuel Stops and fuel purchases that lets the vehicle complete a Trip within its range.
_Avoid_: Route plan, refuelling route

**Vehicle Profile**:
The tank capacity and fuel efficiency used to determine range and fuel consumption. The service defaults to a 50-gallon tank at 10 MPG, while a Trip may supply any positive tank capacity for a hypothetical vehicle.
_Avoid_: Car settings, vehicle configuration

**Fuel Stop**:
A Fuel Station selected for a fuel purchase during a Fuel Plan.
_Avoid_: Waypoint

**Route Corridor**:
The area close enough to a Route for a Fuel Station to be considered without recalculating the Route through that station.
_Avoid_: Search radius

**Candidate Station**:
A Fuel Station whose known or approximate location falls within the Route Corridor.
_Avoid_: Nearby station

**Coordinate Precision**:
The declared accuracy of a Fuel Station location, distinguishing an address-level match from a locality-level approximation.
_Avoid_: Location quality

**Starting Fuel**:
A full tank available at the Trip origin. Its earlier purchase cost is not part of the Trip's fuel cost.
_Avoid_: Free fuel

**Trip Fuel Cost**:
The total cost of fuel purchased at Fuel Stops after departure. It excludes the unknown historical cost of Starting Fuel.
_Avoid_: Total fuel cost

**Supported Area**:
The contiguous 48 United States. Alaska, Hawaii, territories, Canada, and disconnected road journeys are outside the planning domain.
_Avoid_: USA, North America
