

        // Get container elements
        const containers = document.querySelectorAll('.container');

        // Add click event listener to sidebar toggle
        sidebarToggle.addEventListener('click', function () {
        
        });

        // Add click event listener to nav links
        const navLinks = document.querySelectorAll('.nav-links a');
        navLinks.forEach(function (link) {
            link.addEventListener('click', function (e) {
                e.preventDefault();

                // Get container name from data attribute
                const containerName = link.getAttribute('data-container');

                // Hide all containers
                containers.forEach(function (container) {
                    container.style.display = 'none';
                });

                // Show the selected container
                const selectedContainer = document.getElementById(containerName + '-container');
                selectedContainer.style.display = 'block';
            });
        });