document.getElementById("service-form").addEventListener("submit", function(event) {
  event.preventDefault(); // Prevent default form submission

  const form = document.getElementById("service-form");
  
  // Capture form data for CRM
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());
  
  // Send data to CRM first (invisible to user)
  sendFormDataToCRM(data);

  // Send the form data using EmailJS (existing functionality)
  emailjs.sendForm("service_tyc0213", "template_32q43sm", form, "Prx0yDnr-5MlTe-vB")
    .then(function(response) {
      alert("✅ Your inquiry has been submitted successfully!");
      closeModal(); // Close the modal after submission
      form.reset(); // Reset the form
    }, function(error) {
      alert("❌ Failed to submit the inquiry. Please try again.");
      console.error("EmailJS Error:", error);
    });
});

// Function to send form data to CRM API
async function sendFormDataToCRM(formData) {
  try {
    const crmData = {
      form_type: 'service_inquiry',
      service_type: formData.service || '',
      contact_info: {
        name: formData.name || '',
        email: formData.email || '',
        phone: formData.phone || ''
      },
      form_data: formData,
      timestamp: new Date().toISOString(),
      source: 'website_form'
    };

    // Try to get CSRF token
    const csrfToken = getCSRFToken();
    const headers = {
      'Content-Type': 'application/json'
    };
    
    // Only add CSRF token if we have one
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }

    const response = await fetch('/api/integrations/webhooks/emailjs/', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(crmData)
    });

    if (response.ok) {
      console.log('Form data sent to CRM successfully');
    } else {
      console.warn('Failed to send form data to CRM:', response.status);
    }
  } catch (error) {
    // Silently handle errors - don't disrupt user experience
    console.warn('Error sending form data to CRM:', error);
  }
}

// Function to get CSRF token
function getCSRFToken() {
  // Get CSRF token from cookie or meta tag
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  
  if (cookieValue) {
    return cookieValue;
  }

  // Fallback: get from meta tag
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  return metaTag ? metaTag.getAttribute('content') : '';
}
