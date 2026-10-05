/**
 * Re:Learn - Flashcards Spaced Repetition Controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  const user = await window.initRelearnHeader('cards');
  if (!user) return;

  let cards = [];
  let currentCardIdx = 0;

  const activeCardWrapper = document.getElementById('activeCardWrapper');
  const activeCardInner = document.getElementById('activeCardInner');
  const cardFrontTitle = document.getElementById('cardFrontTitle');
  const cardFrontCodeSnippet = document.getElementById('cardFrontCodeSnippet');
  const cardBackConceptText = document.getElementById('cardBackConceptText');
  const cardBackFixText = document.getElementById('cardBackFixText');
  const cardBoxTag = document.getElementById('cardBoxTag');
  const cardIndexTracker = document.getElementById('cardIndexTracker');
  const cardRatingControls = document.getElementById('cardRatingControls');
  const noCardsNotice = document.getElementById('noCardsNotice');

  const btnCardAgain = document.getElementById('btnCardAgain');
  const btnCardGotIt = document.getElementById('btnCardGotIt');

  // Flip Card on Click
  activeCardWrapper.addEventListener('click', () => {
    activeCardInner.classList.toggle('flipped');
  });

  async function loadCards() {
    try {
      const res = await fetch(`/api/flashcards?student_id=${user.id}`);
      if (!res.ok) throw new Error('Failed to load flashcards.');
      const data = await res.json();
      cards = data.cards || [];
      currentCardIdx = 0;
      renderCurrentCard();
    } catch (err) {
      console.error('Error fetching cards:', err);
    }
  }

  function renderCurrentCard() {
    activeCardInner.classList.remove('flipped');

    if (cards.length === 0 || currentCardIdx >= cards.length) {
      activeCardWrapper.style.display = 'none';
      cardRatingControls.style.display = 'none';
      noCardsNotice.style.display = 'block';
      return;
    }

    activeCardWrapper.style.display = 'block';
    cardRatingControls.style.display = 'flex';
    noCardsNotice.style.display = 'none';

    const card = cards[currentCardIdx];
    cardIndexTracker.textContent = `Card ${currentCardIdx + 1} of ${cards.length}`;
    cardBoxTag.textContent = `Box ${card.box || 1} (Spaced Interval)`;
    cardFrontTitle.textContent = card.title;
    cardFrontCodeSnippet.innerHTML = window.highlightCCode(card.front_code);
    cardBackConceptText.textContent = card.back_concept;
    cardBackFixText.textContent = card.back_fix;
  }

  async function rateCard(rating) {
    const card = cards[currentCardIdx];
    if (!card) return;

    try {
      await fetch(`/api/flashcards/${card.id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: user.id,
          rating: rating
        })
      });

      window.showToast(rating === 'got_it' ? 'Card advanced to next box! ✓' : 'Card will be reviewed again soon.', 'info', 1800);
      currentCardIdx++;
      renderCurrentCard();
    } catch (err) {
      console.error(err);
    }
  }

  btnCardAgain.addEventListener('click', () => rateCard('again'));
  btnCardGotIt.addEventListener('click', () => rateCard('got_it'));

  loadCards();
});
