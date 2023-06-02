    // Function to get the current time and date
    function getCurrentDateTime() {
        const greetingElement = document.getElementById('greeting-text');
        const timeElement = document.getElementById('time');
       const dateElement = document.getElementById('date');


  // Get current date and time
  const currentDate = new Date();
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  const formattedDate = currentDate.toLocaleDateString('en-US', options);
  const currentTime = currentDate.toLocaleTimeString('en-US');

  // Update time and date elements
  timeElement.textContent = currentTime;
  dateElement.textContent = formattedDate;

  // Set greeting based on the current time
  const currentHour = currentDate.getHours();
  let greeting = '';
  if (currentHour < 12) {
      greeting = 'Good morning';
  } else if (currentHour < 18) {
      greeting = 'Good afternoon';
  } else {
      greeting = 'Good evening';
  }

  // Update greeting element
  greetingElement.textContent = greeting;
}

// Call the function to display initial time, date, and greeting
getCurrentDateTime();

// Update time, date, and greeting every second
setInterval(getCurrentDateTime, 1000);