fetch('data/conflicting.json')
  .then(response => response.json())
  .then(conflictingData => {
    const container = document.getElementById('conflict-table');
    
    // Build an HTML table or list of conflicts
    let html = '<table border="1"><tr><th>Term</th><th>Definition</th><th>Discipline</th></tr>';
    
    conflictingData.forEach(item => {
      html += `<tr>
                 <td>${item.term}</td>
                 <td>${item.definition}</td>
                 <td>${item.discipline}</td>
               </tr>`;
    });
    
    html += '</table>';
    container.innerHTML = html;
  });
