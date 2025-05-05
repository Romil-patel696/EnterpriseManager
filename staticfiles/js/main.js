/**
 * Main JavaScript file for SME Application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Notification badge
    const notificationBadge = document.getElementById('notification-badge');
    if (notificationBadge) {
        // Example: update notification count from server periodically
        // This would typically come from an API call
        setInterval(function() {
            fetch('/api/notifications/unread-count/')
                .then(response => response.json())
                .then(data => {
                    if (data.count > 0) {
                        notificationBadge.textContent = data.count;
                        notificationBadge.classList.remove('d-none');
                    } else {
                        notificationBadge.classList.add('d-none');
                    }
                })
                .catch(error => console.error('Error fetching notifications:', error));
        }, 60000); // Check every minute
    }

    // DataTables initialization
    const dataTables = document.querySelectorAll('.datatable');
    if (dataTables.length > 0) {
        dataTables.forEach(table => {
            $(table).DataTable({
                responsive: true,
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search...",
                }
            });
        });
    }

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Inventory - Quick View Modal
    const quickViewButtons = document.querySelectorAll('.btn-quick-view');
    if (quickViewButtons.length > 0) {
        quickViewButtons.forEach(button => {
            button.addEventListener('click', function() {
                const productId = this.getAttribute('data-product-id');
                fetch(`/inventory/api/products/${productId}/`)
                    .then(response => response.json())
                    .then(product => {
                        document.getElementById('quickViewProductName').textContent = product.name;
                        document.getElementById('quickViewProductCategory').textContent = product.category;
                        document.getElementById('quickViewProductSKU').textContent = product.sku;
                        document.getElementById('quickViewProductPrice').textContent = `$${product.price}`;
                        document.getElementById('quickViewProductStock').textContent = product.current_stock;
                        if (product.image) {
                            document.getElementById('quickViewProductImage').src = product.image;
                            document.getElementById('quickViewProductImage').classList.remove('d-none');
                        } else {
                            document.getElementById('quickViewProductImage').classList.add('d-none');
                        }
                        const modal = new bootstrap.Modal(document.getElementById('quickViewModal'));
                        modal.show();
                    })
                    .catch(error => console.error('Error fetching product:', error));
            });
        });
    }

    // Attendance - Calendar View
    const attendanceCalendar = document.getElementById('attendance-calendar');
    if (attendanceCalendar) {
        const today = new Date();
        const currentMonth = today.getMonth();
        const currentYear = today.getFullYear();
        
        // Function to render calendar
        function renderCalendar(month, year) {
            const firstDay = new Date(year, month, 1);
            const daysInMonth = new Date(year, month + 1, 0).getDate();
            const startingDay = firstDay.getDay(); // Day of week (0-6)
            
            // Update calendar header
            document.getElementById('calendar-month-year').textContent = 
                `${firstDay.toLocaleString('default', { month: 'long' })} ${year}`;
            
            let calendarBody = document.getElementById('calendar-body');
            // Clear existing rows
            calendarBody.innerHTML = '';
            
            // Creating calendar cells
            let date = 1;
            for (let i = 0; i < 6; i++) {
                let row = document.createElement('tr');
                
                for (let j = 0; j < 7; j++) {
                    if (i === 0 && j < startingDay) {
                        // Empty cells before start of month
                        let cell = document.createElement('td');
                        cell.classList.add('calendar-day', 'empty');
                        row.appendChild(cell);
                    } else if (date > daysInMonth) {
                        // Break if we've reached end of month
                        break;
                    } else {
                        // Fill with date
                        let cell = document.createElement('td');
                        cell.classList.add('calendar-day');
                        
                        // Highlight current day
                        if (date === today.getDate() && year === today.getFullYear() && month === today.getMonth()) {
                            cell.classList.add('today');
                        }
                        
                        // Weekend styling
                        if (j === 0 || j === 6) { // Sunday or Saturday
                            cell.classList.add('weekend');
                        }
                        
                        // Date number
                        let dateDiv = document.createElement('div');
                        dateDiv.textContent = date;
                        cell.appendChild(dateDiv);
                        
                        // Example: Add attendance status
                        // This would come from actual attendance data
                        const checkDate = new Date(year, month, date);
                        if (checkDate <= today) {
                            const attendanceStatus = document.createElement('div');
                            // Randomize for demo purposes - would be actual status in production
                            const statuses = ['present', 'absent', 'late'];
                            const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];
                            attendanceStatus.className = `attendance-status ${randomStatus}`;
                            cell.appendChild(attendanceStatus);
                        }
                        
                        row.appendChild(cell);
                        date++;
                    }
                }
                
                if (date > daysInMonth) {
                    // Stop creating rows if we've reached end of month
                    calendarBody.appendChild(row);
                    break;
                }
                
                calendarBody.appendChild(row);
            }
        }
        
        // Initial render
        renderCalendar(currentMonth, currentYear);
        
        // Previous month button
        document.getElementById('prev-month').addEventListener('click', function() {
            // Get current displayed month
            const monthYear = document.getElementById('calendar-month-year').textContent.split(' ');
            const month = new Date(Date.parse(`${monthYear[0]} 1, ${monthYear[1]}`)).getMonth();
            const year = parseInt(monthYear[1]);
            
            let newMonth, newYear;
            if (month === 0) {
                newMonth = 11;
                newYear = year - 1;
            } else {
                newMonth = month - 1;
                newYear = year;
            }
            
            renderCalendar(newMonth, newYear);
        });
        
        // Next month button
        document.getElementById('next-month').addEventListener('click', function() {
            // Get current displayed month
            const monthYear = document.getElementById('calendar-month-year').textContent.split(' ');
            const month = new Date(Date.parse(`${monthYear[0]} 1, ${monthYear[1]}`)).getMonth();
            const year = parseInt(monthYear[1]);
            
            let newMonth, newYear;
            if (month === 11) {
                newMonth = 0;
                newYear = year + 1;
            } else {
                newMonth = month + 1;
                newYear = year;
            }
            
            renderCalendar(newMonth, newYear);
        });
    }
});
