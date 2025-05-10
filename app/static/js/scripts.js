// Custom JavaScript for CitySeva Web Application

// Function to initialize the toast messages
function initializeToasts() {
    const toastElList = document.querySelectorAll('.toast');
    const toastList = [...toastElList].map(toastEl => new bootstrap.Toast(toastEl));
    toastList.forEach(toast => toast.show());
}

// Function to initialize the complaint submission map
function initializeComplaintMap() {
    // Check if the map element exists
    const mapElement = document.getElementById('complaint-map');
    if (!mapElement) return;

    // Check if latitude and longitude inputs exist
    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');
    
    if (!latInput || !lngInput) return; // Exit if these elements don't exist

    // Initialize the map
    const map = L.map('complaint-map').setView([20.5937, 78.9629], 5); // Default center on India

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Add marker for the complaint location (if editing a complaint)
    let marker;
    if (latInput.value && lngInput.value) {
        const lat = parseFloat(latInput.value);
        const lng = parseFloat(lngInput.value);
        
        map.setView([lat, lng], 15);
        marker = L.marker([lat, lng]).addTo(map);
    }

    // Handle map clicks to set location
    map.on('click', function(e) {
        // Update hidden form fields
        latInput.value = e.latlng.lat;
        lngInput.value = e.latlng.lng;
        
        // Update or add marker
        if (marker) {
            marker.setLatLng(e.latlng);
        } else {
            marker = L.marker(e.latlng).addTo(map);
        }
        
        // Check if location element exists
        const locationInput = document.getElementById('location');
        if (!locationInput) return;
        
        // Reverse geocode to get address
        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${e.latlng.lat}&lon=${e.latlng.lng}`)
            .then(response => response.json())
            .then(data => {
                if (data.display_name) {
                    locationInput.value = data.display_name;
                }
            })
            .catch(error => console.error('Error getting location name:', error));
    });
}

// Function to initialize the dashboard charts
function initializeDashboardCharts() {
    // Check if we're on the dashboard page
    const categoryChartElement = document.getElementById('categoryChart');
    const priorityChartElement = document.getElementById('priorityChart');
    const timelineChartElement = document.getElementById('timelineChart');
    
    if (!categoryChartElement && !priorityChartElement && !timelineChartElement) return;
    
    // Fetch the category data
    if (categoryChartElement) {
        fetch('/api/stats/category')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    new Chart(categoryChartElement, {
                        type: 'pie',
                        data: {
                            labels: data.data.labels,
                            datasets: [{
                                data: data.data.values,
                                backgroundColor: [
                                    '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', 
                                    '#e74a3b', '#858796', '#5a5c69', '#f8f9fc'
                                ],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom'
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error fetching category data:', error));
    }
    
    // Fetch the priority data
    if (priorityChartElement) {
        fetch('/api/stats/priority')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    new Chart(priorityChartElement, {
                        type: 'doughnut',
                        data: {
                            labels: data.data.labels,
                            datasets: [{
                                data: data.data.values,
                                backgroundColor: [
                                    '#5cb85c', '#f0ad4e', '#d9534f', '#8b0000'
                                ],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom'
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error fetching priority data:', error));
    }
    
    // Fetch the timeline data
    if (timelineChartElement) {
        fetch('/api/stats/timeline')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    new Chart(timelineChartElement, {
                        type: 'line',
                        data: {
                            labels: data.data.labels,
                            datasets: data.data.datasets.map((dataset, index) => ({
                                label: dataset.label,
                                data: dataset.data,
                                borderColor: index === 0 ? '#4e73df' : '#1cc88a',
                                backgroundColor: 'transparent',
                                borderWidth: 2,
                                pointBackgroundColor: index === 0 ? '#4e73df' : '#1cc88a',
                                tension: 0.3
                            }))
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error fetching timeline data:', error));
    }
}

// Function to initialize the complaints map
function initializeComplaintsMap() {
    // Check if the map element exists
    const mapElement = document.getElementById('complaints-map');
    if (!mapElement) return;
    
    // Check if map is already initialized
    if (mapElement._leaflet_id) {
        console.log('Map already initialized');
        return;
    }

    // Initialize the map
    const map = L.map('complaints-map').setView([20.5937, 78.9629], 5); // Default center on India

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Fetch complaint data for the map
    fetch('/api/map/complaints')
        .then(response => response.json())
        .then(data => {
            // Add GeoJSON layer with custom styling based on status
            L.geoJSON(data, {
                pointToLayer: function(feature, latlng) {
                    // Choose marker color based on status
                    let markerColor = '#f0ad4e'; // Default/pending - yellow
                    
                    if (feature.properties.status === 'in_progress') {
                        markerColor = '#5bc0de'; // Blue
                    } else if (feature.properties.status === 'resolved') {
                        markerColor = '#5cb85c'; // Green
                    } else if (feature.properties.status === 'rejected') {
                        markerColor = '#d9534f'; // Red
                    }
                    
                    return L.circleMarker(latlng, {
                        radius: 8,
                        fillColor: markerColor,
                        color: '#fff',
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8
                    });
                },
                onEachFeature: function(feature, layer) {
                    // Create popup content
                    let popupContent = `
                        <strong>${feature.properties.title}</strong><br>
                        Category: ${feature.properties.category}<br>
                        Status: ${feature.properties.status}<br>
                        Priority: ${feature.properties.priority}<br>
                        Date: ${feature.properties.created_at}<br>
                        <a href="/complaint/${feature.properties.id}" class="btn btn-sm btn-primary mt-2">View Details</a>
                    `;
                    
                    layer.bindPopup(popupContent);
                }
            }).addTo(map);
            
            // If we have complaints, fit the map to their bounds
            if (data.features && data.features.length > 0) {
                const bounds = L.geoJSON(data).getBounds();
                map.fitBounds(bounds);
            }
        })
        .catch(error => console.error('Error fetching map data:', error));
}

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Initialize toast messages
    initializeToasts();
    
    // Initialize complaint submission map
    initializeComplaintMap();
    
    // Initialize dashboard charts
    initializeDashboardCharts();
    
    // Initialize complaints map
    initializeComplaintsMap();
    
    // Handle complaint status updates via API
    const statusUpdateButtons = document.querySelectorAll('.update-status-btn');
    statusUpdateButtons.forEach(button => {
        button.addEventListener('click', function() {
            const complaintId = this.dataset.complaintId;
            const newStatus = this.dataset.status;
            const comment = prompt("Enter a comment for this status update (optional):");
            
            if (complaintId && newStatus) {
                fetch(`/api/complaints/${complaintId}/status`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        status: newStatus,
                        comment: comment || `Status updated to ${newStatus}`
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Reload the page to show updated status
                        window.location.reload();
                    } else {
                        alert("Error updating complaint status: " + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error updating status:', error);
                    alert("Error updating complaint status. Please try again.");
                });
            }
        });
    });
}); 