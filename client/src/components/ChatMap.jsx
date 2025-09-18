import {React, useRef, useState} from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { setIsChatMapOpen } from '../slices/chatmap'
import Globe from 'react-globe.gl';
import globeImage from '../assets/earth-dark.jpg';
import {X} from 'lucide-react'
import * as THREE from 'three'

const ChatMap = () => {
  const isChatMapOpen = useSelector((state) => state.chatMap.isChatMapOpen)
  const dispatch = useDispatch()

  const [mapType,setMapType] = useState('Label')


  const globeRef = useRef(null)

  const printfnc= (e) =>{
    console.log(e);
  }

  

  const globeReady = () => {
      if (globeRef.current) {
        globeRef.current.controls().autoRotate = true;  //rotating
        globeRef.current.controls().enableZoom = false;
  
        globeRef.current.pointOfView({
          lat: 22.680114270049245,
          lng: 72.9587054670363,
          altitude: 1.8,
        });
      }
    };
    if(!isChatMapOpen){
      return null
    }

    // Demo labels data for major cities and locations
    const labelsData = [
      // Major Cities
      { lat: 40.7128, lng: -74.0060, text: 'New York', color: '#ff6b6b', size: 1.8, altitude: 0.01 },
      { lat: 51.5074, lng: -0.1278, text: 'London', color: '#4ecdc4', size: 1.7, altitude: 0.01 },
      { lat: 35.6762, lng: 139.6503, text: 'Tokyo', color: '#45b7d1', size: 1.6, altitude: 0.01 },
      { lat: 48.8566, lng: 2.3522, text: 'Paris', color: '#96ceb4', size: 1.5, altitude: 0.01 },
      { lat: 55.7558, lng: 37.6176, text: 'Moscow', color: '#feca57', size: 1.5, altitude: 0.01 },
      { lat: -33.8688, lng: 151.2093, text: 'Sydney', color: '#ff9ff3', size: 1.5, altitude: 0.01 },
      { lat: 19.0760, lng: 72.8777, text: 'Mumbai', color: '#ff6b6b', size: 1.5, altitude: 0.01 },
      { lat: 39.9042, lng: 116.4074, text: 'Beijing', color: '#4ecdc4', size: 1.5, altitude: 0.01 },
      { lat: -22.9068, lng: -43.1729, text: 'Rio de Janeiro', color: '#45b7d1', size: 1.5, altitude: 0.01 },
      { lat: 25.2048, lng: 55.2708, text: 'Dubai', color: '#96ceb4', size: 1.4, altitude: 0.01 },
      
      // Landmarks
      { lat: 27.1751, lng: 78.0421, text: 'Taj Mahal', color: '#feca57', size: 1.4, altitude: 0.02 },
      { lat: 29.9792, lng: 31.1342, text: 'Pyramids', color: '#ff9ff3', size: 1.4, altitude: 0.02 },
      { lat: 48.8584, lng: 2.2945, text: 'Eiffel Tower', color: '#ff6b6b', size: 1.4, altitude: 0.02 },
      { lat: 40.4319, lng: -3.6904, text: 'Madrid', color: '#4ecdc4', size: 1.4, altitude: 0.01 },
      { lat: 52.5200, lng: 13.4050, text: 'Berlin', color: '#45b7d1', size: 1.4, altitude: 0.01 },
      
      // Random interesting locations
      { lat: 64.1466, lng: -21.9426, text: 'Reykjavik', color: '#96ceb4', size: 1.4, altitude: 0.01 },
      { lat: -1.2921, lng: 36.8219, text: 'Nairobi', color: '#feca57', size: 1.4, altitude: 0.01 },
      { lat: 1.3521, lng: 103.8198, text: 'Singapore', color: '#ff9ff3', size: 1.4, altitude: 0.01 },
      { lat: 37.5665, lng: 126.9780, text: 'Seoul', color: '#ff6b6b', size: 1.4, altitude: 0.01 },
      { lat: 41.9028, lng: 12.4964, text: 'Rome', color: '#4ecdc4', size: 1.4, altitude: 0.01 }
    ];

    // Hex Bin Layer Data - Random points for demonstration
    const hexBinPointsData = [
      // North America
      { lat: 40.7128, lng: -74.0060, weight: 15 }, // New York
      { lat: 40.7128, lng: -74.0060, weight: 12 }, // New York (duplicate for density)
      { lat: 40.7128, lng: -74.0060, weight: 8 },  // New York (duplicate for density)
      { lat: 34.0522, lng: -118.2437, weight: 10 }, // Los Angeles
      { lat: 34.0522, lng: -118.2437, weight: 7 },  // Los Angeles
      { lat: 41.8781, lng: -87.6298, weight: 9 },   // Chicago
      { lat: 29.7604, lng: -95.3698, weight: 6 },   // Houston
      { lat: 25.7617, lng: -80.1918, weight: 5 },   // Miami
      { lat: 43.6532, lng: -79.3832, weight: 8 },   // Toronto
      { lat: 49.2827, lng: -123.1207, weight: 4 },  // Vancouver
      
      // Europe
      { lat: 51.5074, lng: -0.1278, weight: 14 },   // London
      { lat: 51.5074, lng: -0.1278, weight: 11 },   // London
      { lat: 48.8566, lng: 2.3522, weight: 12 },    // Paris
      { lat: 48.8566, lng: 2.3522, weight: 9 },     // Paris
      { lat: 52.5200, lng: 13.4050, weight: 10 },   // Berlin
      { lat: 41.9028, lng: 12.4964, weight: 8 },    // Rome
      { lat: 40.4319, lng: -3.6904, weight: 7 },    // Madrid
      { lat: 55.7558, lng: 37.6176, weight: 13 },   // Moscow
      { lat: 59.9311, lng: 10.7579, weight: 3 },    // Oslo
      { lat: 64.1466, lng: -21.9426, weight: 2 },   // Reykjavik
      
      // Asia
      { lat: 35.6762, lng: 139.6503, weight: 16 },  // Tokyo
      { lat: 35.6762, lng: 139.6503, weight: 13 },  // Tokyo
      { lat: 35.6762, lng: 139.6503, weight: 10 },  // Tokyo
      { lat: 37.5665, lng: 126.9780, weight: 11 },  // Seoul
      { lat: 39.9042, lng: 116.4074, weight: 15 },  // Beijing
      { lat: 39.9042, lng: 116.4074, weight: 12 },  // Beijing
      { lat: 22.3193, lng: 114.1694, weight: 9 },   // Hong Kong
      { lat: 1.3521, lng: 103.8198, weight: 8 },    // Singapore
      { lat: 19.0760, lng: 72.8777, weight: 14 },   // Mumbai
      { lat: 19.0760, lng: 72.8777, weight: 11 },   // Mumbai
      { lat: 28.6139, lng: 77.2090, weight: 10 },   // New Delhi
      { lat: 13.7563, lng: 100.5018, weight: 6 },   // Bangkok
      
      // Australia & Oceania
      { lat: -33.8688, lng: 151.2093, weight: 9 },  // Sydney
      { lat: -37.8136, lng: 144.9631, weight: 7 },  // Melbourne
      { lat: -31.9505, lng: 115.8605, weight: 4 },  // Perth
      { lat: -36.8485, lng: 174.7633, weight: 3 },  // Auckland
      
      // South America
      { lat: -22.9068, lng: -43.1729, weight: 11 }, // Rio de Janeiro
      { lat: -23.5505, lng: -46.6333, weight: 10 }, // São Paulo
      { lat: -34.6118, lng: -58.3960, weight: 8 },  // Buenos Aires
      { lat: -12.0464, lng: -77.0428, weight: 5 },  // Lima
      
      // Africa
      { lat: -26.2041, lng: 28.0473, weight: 7 },   // Johannesburg
      { lat: -33.9249, lng: 18.4241, weight: 6 },   // Cape Town
      { lat: -1.2921, lng: 36.8219, weight: 5 },    // Nairobi
      { lat: 6.5244, lng: 3.3792, weight: 4 },      // Lagos
      
      // Middle East
      { lat: 25.2048, lng: 55.2708, weight: 6 },    // Dubai
      { lat: 31.7683, lng: 35.2137, weight: 3 },    // Jerusalem
      { lat: 29.3117, lng: 47.4818, weight: 4 },    // Kuwait City
    ];

    // Heatmap Data - Concentrated around Indian Ocean region
    const heatmapsData = [
      // India - West Coast
      { lat: 19.0760, lng: 72.8777, weight: 0.9 }, // Mumbai
      { lat: 19.0760, lng: 72.8777, weight: 0.8 }, // Mumbai (duplicate for density)
      { lat: 19.0760, lng: 72.8777, weight: 0.7 }, // Mumbai (duplicate for density)
      { lat: 15.2993, lng: 74.1240, weight: 0.6 }, // Goa
      { lat: 15.2993, lng: 74.1240, weight: 0.5 }, // Goa
      { lat: 12.9716, lng: 77.5946, weight: 0.7 }, // Bangalore
      { lat: 12.9716, lng: 77.5946, weight: 0.6 }, // Bangalore
      { lat: 9.9312, lng: 76.2673, weight: 0.4 },  // Kochi
      { lat: 8.5241, lng: 76.9366, weight: 0.3 },  // Trivandrum
      { lat: 8.5241, lng: 76.9366, weight: 0.2 },  // Trivandrum
      
      // India - East Coast
      { lat: 13.0827, lng: 80.2707, weight: 0.8 }, // Chennai
      { lat: 13.0827, lng: 80.2707, weight: 0.7 }, // Chennai
      { lat: 17.6868, lng: 83.2185, weight: 0.5 }, // Visakhapatnam
      { lat: 22.5726, lng: 88.3639, weight: 0.9 }, // Kolkata
      { lat: 22.5726, lng: 88.3639, weight: 0.8 }, // Kolkata
      { lat: 20.2961, lng: 85.8245, weight: 0.4 }, // Bhubaneswar
      { lat: 16.5062, lng: 80.6480, weight: 0.3 }, // Vijayawada
      
      // Sri Lanka
      { lat: 6.9271, lng: 79.8612, weight: 0.8 },  // Colombo
      { lat: 6.9271, lng: 79.8612, weight: 0.7 },  // Colombo
      { lat: 6.9271, lng: 79.8612, weight: 0.6 },  // Colombo
      { lat: 7.2906, lng: 80.6337, weight: 0.4 },  // Kandy
      { lat: 9.6615, lng: 80.0255, weight: 0.3 },  // Jaffna
      
      // Maldives
      { lat: 4.1755, lng: 73.5093, weight: 0.6 },  // Malé
      { lat: 4.1755, lng: 73.5093, weight: 0.5 },  // Malé
      { lat: 4.1755, lng: 73.5093, weight: 0.4 },  // Malé
      { lat: 3.2028, lng: 73.2207, weight: 0.2 },  // Addu City
      { lat: 5.5554, lng: 73.2207, weight: 0.2 },  // Kulhudhuffushi
      
      // Bangladesh
      { lat: 23.8103, lng: 90.4125, weight: 0.8 }, // Dhaka
      { lat: 23.8103, lng: 90.4125, weight: 0.7 }, // Dhaka
      { lat: 22.3569, lng: 91.7832, weight: 0.6 }, // Chittagong
      { lat: 22.3569, lng: 91.7832, weight: 0.5 }, // Chittagong
      { lat: 24.3636, lng: 88.6241, weight: 0.3 }, // Rajshahi
      
      // Myanmar
      { lat: 16.8661, lng: 96.1951, weight: 0.7 }, // Yangon
      { lat: 16.8661, lng: 96.1951, weight: 0.6 }, // Yangon
      { lat: 21.9162, lng: 95.9560, weight: 0.4 }, // Mandalay
      { lat: 20.1448, lng: 92.8965, weight: 0.3 }, // Sittwe
      { lat: 15.8700, lng: 100.9925, weight: 0.5 }, // Bangkok (Thailand)
      
      // Indonesia - Sumatra
      { lat: -6.2088, lng: 106.8456, weight: 0.9 }, // Jakarta
      { lat: -6.2088, lng: 106.8456, weight: 0.8 }, // Jakarta
      { lat: -6.2088, lng: 106.8456, weight: 0.7 }, // Jakarta
      { lat: -0.7893, lng: 113.9213, weight: 0.4 }, // Pontianak
      { lat: 1.3521, lng: 103.8198, weight: 0.8 },  // Singapore
      { lat: 1.3521, lng: 103.8198, weight: 0.7 },  // Singapore
      
      // Malaysia
      { lat: 3.1390, lng: 101.6869, weight: 0.7 },  // Kuala Lumpur
      { lat: 3.1390, lng: 101.6869, weight: 0.6 },  // Kuala Lumpur
      { lat: 5.4164, lng: 100.3327, weight: 0.4 },  // Penang
      { lat: 1.4927, lng: 103.7414, weight: 0.3 },  // Johor Bahru
      
      // Thailand - Andaman Sea
      { lat: 7.8804, lng: 98.3923, weight: 0.6 },   // Phuket
      { lat: 7.8804, lng: 98.3923, weight: 0.5 },   // Phuket
      { lat: 7.8804, lng: 98.3923, weight: 0.4 },   // Phuket
      { lat: 8.0863, lng: 98.3063, weight: 0.3 },   // Krabi
      { lat: 9.1382, lng: 99.3215, weight: 0.2 },   // Surat Thani
      
      // Arabian Sea - Pakistan
      { lat: 24.8607, lng: 67.0011, weight: 0.8 },  // Karachi
      { lat: 24.8607, lng: 67.0011, weight: 0.7 },  // Karachi
      { lat: 24.8607, lng: 67.0011, weight: 0.6 },  // Karachi
      { lat: 25.3960, lng: 68.3578, weight: 0.4 },  // Hyderabad
      { lat: 31.5204, lng: 74.3587, weight: 0.5 },  // Lahore
      
      // Arabian Sea - Iran
      { lat: 27.1833, lng: 56.2667, weight: 0.5 },  // Bandar Abbas
      { lat: 27.1833, lng: 56.2667, weight: 0.4 },  // Bandar Abbas
      { lat: 29.5918, lng: 50.3176, weight: 0.3 },  // Bushehr
      { lat: 25.2048, lng: 55.2708, weight: 0.6 },  // Dubai
      { lat: 25.2048, lng: 55.2708, weight: 0.5 },  // Dubai
      
      // East Africa - Indian Ocean Coast
      { lat: -1.2921, lng: 36.8219, weight: 0.5 },  // Nairobi
      { lat: -1.2921, lng: 36.8219, weight: 0.4 },  // Nairobi
      { lat: -4.0437, lng: 39.6682, weight: 0.4 },  // Mombasa
      { lat: -4.0437, lng: 39.6682, weight: 0.3 },  // Mombasa
      { lat: -6.7924, lng: 39.2083, weight: 0.3 },  // Dar es Salaam
      { lat: -6.7924, lng: 39.2083, weight: 0.2 },  // Dar es Salaam
      { lat: -18.8792, lng: 47.5079, weight: 0.2 }, // Antananarivo (Madagascar)
      { lat: -18.8792, lng: 47.5079, weight: 0.1 }, // Antananarivo
      
      // Australia - West Coast
      { lat: -31.9505, lng: 115.8605, weight: 0.4 }, // Perth
      { lat: -31.9505, lng: 115.8605, weight: 0.3 }, // Perth
      { lat: -32.0567, lng: 115.7437, weight: 0.2 }, // Fremantle
      { lat: -33.8688, lng: 151.2093, weight: 0.5 }, // Sydney
      { lat: -33.8688, lng: 151.2093, weight: 0.4 }, // Sydney
    ];

    
  
  return (

    <div className="absolute z-10 transition-all duration-300 h-full w-full top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-black overflow-hidden">
      {/* top bar  */}
      <div className="absolute z-20 h-[10vh] px-6 w-full top-0 left-0 bg-gray-800/30 flex flex-col justify-center text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Interactive Globe View</h1>
            <h5 className="text-sm opacity-80">Hex Bin Data Visualization with Indian Ocean Heatmap</h5>
          </div>
          <div className="flex items-center gap-4">
            <button className="text-white bg-gray-600 px-4 py-2 rounded-md" onClick={() => setMapType("Label")}>Label</button>
            <button className="text-white bg-gray-600 px-4 py-2 rounded-md" onClick={() => setMapType("HexBin")}>HexBin</button>
            <button className="text-white bg-gray-600 px-4 py-2 rounded-md" onClick={() => setMapType("Heatmap")}>Heatmap</button>
          </div>
          <div className="flex items-center gap-4">
            <X onClick={(e) => {
              e.stopPropagation()
              dispatch(setIsChatMapOpen(false))
            }} className="text-white w-8 h-8 cursor-pointer hover:bg-gray-600 rounded-full p-1"/>
          </div>
        </div>
      </div>

       {/* modals   */}
       {mapType=="Label" && (
      <Globe
      globeImageUrl={globeImage}
      backgroundColor='#08070e'
      ref={globeRef}
      onGlobeReady={globeReady}
      globeOffset={[0,0]}
      animateIn={true}    //rotating entry
      showAtmosphere={true}
      onGlobeClick={printfnc}

        labelsData= {labelsData}
        labelText= "text"
        labelLat= "lat"
        labelLng= "lng"
        labelColor= "color"
        labelSize= "size"
        labelAltitude= "altitude"
        labelIncludeDot={true}
        labelDotRadius={2}
        labelDotOrientation= "bottom"
        labelResolution={10}

      // atmosphere particle
      customLayerData={[...Array(500).keys()].map(() => ({
        lat: (Math.random() - 1) * 360,
        lng: (Math.random() - 1) * 360,
        altitude: Math.random() * 2,
        size: Math.random() * 0.4,
        color: '#faadfd',
      }))}
      customThreeObject={(sliceData) => {
        const { size, color } = sliceData;
        return new THREE.Mesh(new THREE.SphereGeometry(size), new THREE.MeshBasicMaterial({ color }));
      }}
      customThreeObjectUpdate={(obj, sliceData) => {
        const { lat, lng, altitude } = sliceData;
        return Object.assign(obj.position, globeRef.current?.getCoords(lat, lng, altitude));
      }}

      />
    )}

    {mapType=="HexBin" && (
      <Globe
      globeImageUrl={globeImage}
      backgroundColor='#08070e'
      ref={globeRef}
      onGlobeReady={globeReady}
      globeOffset={[0,0]}
      animateIn={true}    //rotating entry
      showAtmosphere={true}
      onGlobeClick={printfnc}
      
      // Hex Bin Layer
      hexBinPointsData={hexBinPointsData}
      hexBinPointLat="lat"
      hexBinPointLng="lng"
      hexBinPointWeight="weight"
      hexBinResolution={4}
      hexMargin={0.1}
      hexAltitude={({ sumWeight }) => sumWeight * 0.02}
      hexTopCurvatureResolution={6}
      hexTopColor={({ sumWeight }) => {
        if (sumWeight > 30) return '#ff4444'; // High density - Red
        if (sumWeight > 20) return '#ff8844'; // Medium-high - Orange
        if (sumWeight > 10) return '#ffaa44'; // Medium - Yellow-orange
        if (sumWeight > 5) return '#44ff44';  // Low-medium - Green
        return '#4444ff'; // Low - Blue
      }}
      hexSideColor={({ sumWeight }) => {
        if (sumWeight > 30) return '#cc2222'; // High density - Dark red
        if (sumWeight > 20) return '#cc6622'; // Medium-high - Dark orange
        if (sumWeight > 10) return '#cc8822'; // Medium - Dark yellow-orange
        if (sumWeight > 5) return '#22cc22';  // Low-medium - Dark green
        return '#2222cc'; // Low - Dark blue
      }}
      hexBinMerge={false}
      hexTransitionDuration={1200}
      hexLabel={({ points, sumWeight, center }) => 
        `<div style="padding: 8px; background: rgba(0,0,0,0.8); color: white; border-radius: 4px;">
          <strong>Hex Bin Data</strong><br/>
          Points: ${points ? points.length : 0}<br/>
          Total Weight: ${sumWeight || 0}<br/>
          Center: ${center && center.lat && center.lng ? `${center.lat.toFixed(2)}, ${center.lng.toFixed(2)}` : 'N/A'}
        </div>`
      }
      onHexClick={(hex, event, coords) => {
        console.log('Hex clicked:', hex, coords);
      }}

      // atmosphere particle
      customLayerData={[...Array(500).keys()].map(() => ({
        lat: (Math.random() - 1) * 360,
        lng: (Math.random() - 1) * 360,
        altitude: Math.random() * 2,
        size: Math.random() * 0.4,
        color: '#faadfd',
      }))}
      customThreeObject={(sliceData) => {
        const { size, color } = sliceData;
        return new THREE.Mesh(new THREE.SphereGeometry(size), new THREE.MeshBasicMaterial({ color }));
      }}
      customThreeObjectUpdate={(obj, sliceData) => {
        const { lat, lng, altitude } = sliceData;
        return Object.assign(obj.position, globeRef.current?.getCoords(lat, lng, altitude));
      }}

      />

    )}

    {mapType=="Heatmap" && (
      <Globe
      globeImageUrl={globeImage}
      backgroundColor='#08070e'
      ref={globeRef}
      onGlobeReady={globeReady}
      globeOffset={[0,0]}
      animateIn={true}    //rotating entry
      showAtmosphere={true}
      onGlobeClick={printfnc}      

      // Heatmap Layer
      heatmapsData={[heatmapsData]}
      heatmapPointLat="lat"
      heatmapPointLng="lng"
      heatmapPointWeight="weight"
      heatmapTopAltitude={0.2}
      heatmapsTransitionDuration={3000}
      enablePointerInteraction={false}



      // atmosphere particle
      customLayerData={[...Array(500).keys()].map(() => ({
        lat: (Math.random() - 1) * 360,
        lng: (Math.random() - 1) * 360,
        altitude: Math.random() * 2,
        size: Math.random() * 0.4,
        color: '#faadfd',
      }))}
      customThreeObject={(sliceData) => {
        const { size, color } = sliceData;
        return new THREE.Mesh(new THREE.SphereGeometry(size), new THREE.MeshBasicMaterial({ color }));
      }}
      customThreeObjectUpdate={(obj, sliceData) => {
        const { lat, lng, altitude } = sliceData;
        return Object.assign(obj.position, globeRef.current?.getCoords(lat, lng, altitude));
      }}

      />
    )}
        </div>



      
    
    
  )
}

export default ChatMap
