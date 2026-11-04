function flipCard(card, prevCard) {
    var front = card.querySelector('.front');
    var back = card.querySelector('.back');
    
    if(prevCard && card !== prevCard) {
        const frontPrevCard = prevCard.querySelector('.front');
        const backPrevCard = prevCard.querySelector('.back');

        frontPrevCard.style.display = 'block';
        backPrevCard.style.display = 'none';
    } 

    if (front.style.display === 'none') {
        front.style.display = 'block';
        back.style.display = 'none';
    } else {
        front.style.display = 'none';
        back.style.display = 'block';
    }
}