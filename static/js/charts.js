// charts.js - Charts for the dashboard

document.addEventListener('DOMContentLoaded', function() {
    // Check if the attendance chart container exists on the page
    const attendanceChartElement = document.getElementById('attendanceChart');
    if (attendanceChartElement) {
        // Get attendance data from the data attribute
        const attendanceData = JSON.parse(attendanceChartElement.dataset.stats || '[]');
        
        if (attendanceData.length > 0) {
            const dates = attendanceData.map(item => {
                // Format date using JavaScript
                const date = new Date(item.date);
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            });
            
            const approved = attendanceData.map(item => item.approved || 0);
            const pending = attendanceData.map(item => item.pending || 0);
            const rejected = attendanceData.map(item => item.rejected || 0);
            
            new Chart(attendanceChartElement, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [
                        {
                            label: 'Approved',
                            data: approved,
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Pending',
                            data: pending,
                            borderColor: '#ffc107',
                            backgroundColor: 'rgba(255, 193, 7, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Rejected',
                            data: rejected,
                            borderColor: '#dc3545',
                            backgroundColor: 'rgba(220, 53, 69, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0 // Only show whole numbers
                            }
                        }
                    }
                }
            });
        }
    }
    
    // Check if the inventory chart container exists on the page
    const inventoryChartElement = document.getElementById('inventoryChart');
    if (inventoryChartElement) {
        // Get inventory data from the data attribute
        const inventoryData = JSON.parse(inventoryChartElement.dataset.categories || '[]');
        
        if (inventoryData.length > 0) {
            const categories = inventoryData.map(item => item.category);
            const counts = inventoryData.map(item => item.count);
            const values = inventoryData.map(item => item.total_value || 0);
            
            new Chart(inventoryChartElement, {
                type: 'bar',
                data: {
                    labels: categories,
                    datasets: [
                        {
                            label: 'Product Count',
                            data: counts,
                            backgroundColor: 'rgba(54, 162, 235, 0.5)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Total Value ($)',
                            data: values,
                            backgroundColor: 'rgba(255, 159, 64, 0.5)',
                            borderColor: 'rgba(255, 159, 64, 1)',
                            borderWidth: 1,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Count'
                            },
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Value ($)'
                            },
                            beginAtZero: true,
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    }
                }
            });
        }
    }
});
