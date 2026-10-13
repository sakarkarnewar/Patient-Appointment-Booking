/* =========================================================
   NEXUS HEALTHCARE - APPOINTMENT BOOKING & TRIAGE ENGINE
========================================================= */

document.addEventListener('DOMContentLoaded', () => {
  const doctorRadios = document.querySelectorAll('input[name="doctor_id"]');
  const dateInput = document.getElementById('appointment_date');
  const slotsContainer = document.getElementById('slotsContainer');
  const timeSlotInput = document.getElementById('timeSlotInput');
  const selectedSlotText = document.getElementById('selectedSlotText');
  const symptomsInput = document.getElementById('symptoms');
  const triageBox = document.getElementById('triageSuggestionBox');
  const triageBadge = document.getElementById('triageBadge');
  const triageDoctorName = document.getElementById('triageDoctorName');
  const triageSpecialty = document.getElementById('triageSpecialty');
  const triageNotes = document.getElementById('triageNotes');
  const triageAutoSelectBtn = document.getElementById('triageAutoSelectBtn');
  const symptomChips = document.querySelectorAll('.symptom-chip');
  const bookingForm = document.getElementById('bookingForm');

  let currentRecommendedDocId = null;

  // ----------------- 1. DYNAMIC SLOT AVAILABILITY -----------------
  async function refreshSlots() {
    if (!slotsContainer) return;

    const selectedDocRadio = document.querySelector('input[name="doctor_id"]:checked');
    const doctorId = selectedDocRadio ? selectedDocRadio.value : null;
    const dateVal = dateInput ? dateInput.value : null;

    if (!doctorId || !dateVal) {
      slotsContainer.innerHTML = '<p style="color: var(--slate-400); font-size: 0.88rem; grid-column: 1/-1;">Please select a specialist and date first to load available time slots.</p>';
      if (selectedSlotText) selectedSlotText.textContent = 'None selected';
      if (timeSlotInput) timeSlotInput.value = '';
      return;
    }

    slotsContainer.innerHTML = '<div style="grid-column: 1/-1; color: var(--primary); font-size: 0.88rem; font-weight: 600;">Checking doctor availability...</div>';

    try {
      const response = await fetch(`/api/available-slots?doctor_id=${doctorId}&date=${dateVal}`);
      const data = await response.json();

      slotsContainer.innerHTML = '';

      if (!data.all_slots || data.all_slots.length === 0) {
        slotsContainer.innerHTML = '<p style="color: var(--slate-500); grid-column: 1/-1;">No appointment slots configured for this date.</p>';
        return;
      }

      data.all_slots.forEach(slot => {
        const isBooked = data.booked_slots.includes(slot);
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `slot-btn ${isBooked ? 'booked' : ''}`;
        btn.textContent = slot;

        if (isBooked) {
          btn.disabled = true;
          btn.title = 'Slot already booked';
        } else {
          // If this slot was previously chosen, keep it highlighted
          if (timeSlotInput && timeSlotInput.value === slot) {
            btn.classList.add('selected');
          }

          btn.addEventListener('click', () => {
            document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            if (timeSlotInput) timeSlotInput.value = slot;
            if (selectedSlotText) selectedSlotText.textContent = slot;
          });
        }

        slotsContainer.appendChild(btn);
      });

      // Clear selection if previous slot is now booked
      if (timeSlotInput && timeSlotInput.value && data.booked_slots.includes(timeSlotInput.value)) {
        timeSlotInput.value = '';
        if (selectedSlotText) selectedSlotText.textContent = 'None selected';
      }

    } catch (err) {
      console.error('Failed to fetch slots:', err);
      slotsContainer.innerHTML = '<p style="color: #ef4444; grid-column: 1/-1;">Unable to load slots. Please check your connection.</p>';
    }
  }

  // Bind change listeners for doctor selection & date selection
  doctorRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      refreshSlots();
      // Scroll smoothly to step 2 if on mobile
      const step2 = document.getElementById('step2Card');
      if (step2 && window.innerWidth < 768) {
        step2.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  if (dateInput) {
    dateInput.addEventListener('change', refreshSlots);
  }

  // ----------------- 2. CREATIVE FEATURE: SMART TRIAGE -----------------
  let triageDebounceTimer = null;

  async function performTriage(symptomText) {
    if (!triageBox) return;

    if (!symptomText || symptomText.trim().length < 3) {
      triageBox.classList.remove('active');
      return;
    }

    try {
      const response = await fetch('/api/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symptoms: symptomText })
      });
      const data = await response.json();

      if (data.matched_specialty && data.recommended_doctor_id) {
        currentRecommendedDocId = data.recommended_doctor_id;

        if (triageSpecialty) triageSpecialty.textContent = data.matched_specialty;
        if (triageDoctorName) triageDoctorName.textContent = data.recommended_doctor_name || 'Specialist';
        if (triageNotes) triageNotes.textContent = data.notes;

        if (triageBadge) {
          triageBadge.className = `badge ${data.badge}`;
          triageBadge.textContent = data.level;
        }

        triageBox.classList.add('active');
      } else {
        triageBox.classList.remove('active');
      }
    } catch (err) {
      console.error('Triage error:', err);
    }
  }

  if (symptomsInput) {
    symptomsInput.addEventListener('input', (e) => {
      clearTimeout(triageDebounceTimer);
      triageDebounceTimer = setTimeout(() => {
        performTriage(e.target.value);
      }, 350);
    });
  }

  // Symptom chip helper buttons
  symptomChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const chipText = chip.getAttribute('data-symptom') || chip.textContent.trim();
      if (!symptomsInput) return;

      if (symptomsInput.value.trim().length > 0) {
        symptomsInput.value += ', ' + chipText;
      } else {
        symptomsInput.value = chipText;
      }
      performTriage(symptomsInput.value);
    });
  });

  // 1-Click "Select Recommended Doctor" handler
  if (triageAutoSelectBtn) {
    triageAutoSelectBtn.addEventListener('click', () => {
      if (!currentRecommendedDocId) return;

      const targetRadio = document.querySelector(`input[name="doctor_id"][value="${currentRecommendedDocId}"]`);
      if (targetRadio) {
        targetRadio.checked = true;
        refreshSlots();

        // Highlight visual feedback
        const parentCard = targetRadio.closest('.doctor-card-radio');
        if (parentCard) {
          parentCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
          parentCard.style.transform = 'scale(1.03)';
          setTimeout(() => {
            parentCard.style.transform = '';
          }, 350);
        }
      }
    });
  }

  // ----------------- 3. FORM VALIDATION -----------------
  if (bookingForm) {
    bookingForm.addEventListener('submit', (e) => {
      const selectedDocRadio = document.querySelector('input[name="doctor_id"]:checked');
      if (!selectedDocRadio) {
        e.preventDefault();
        alert('Please choose a doctor before submitting.');
        return;
      }

      if (!dateInput || !dateInput.value) {
        e.preventDefault();
        alert('Please pick an appointment date.');
        return;
      }

      if (!timeSlotInput || !timeSlotInput.value) {
        e.preventDefault();
        alert('Please select an available time slot for your appointment.');
        return;
      }
    });
  }

  // Initial slot load if doctor already pre-selected
  refreshSlots();
});
