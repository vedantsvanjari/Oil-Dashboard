import { create } from 'zustand';

const useNewsStore = create((set) => ({
  newsItems: [],
  isLoadingNews: false,
  newsError: null,
  
  fetchNews: async () => {
    set({ isLoadingNews: true, newsError: null });
    try {
      const response = await fetch('/api/news');
      console.log('News API Response Status:', response.status);
      if (!response.ok) throw new Error('Failed to fetch news');
      const data = await response.json();
      console.log('Raw API Response:', data);
      console.log('Data Length:', data.length);
      if (data.length > 0) {
        console.log('First article:', data[0]);
      }
      
      const mappedNews = data.map((item, index) => {
          const t = item.title.toLowerCase();
          let cat = 'Macro';
          if (t.includes('opec') || t.includes('saudi')) cat = 'OPEC';
          else if (t.includes('tanker') || t.includes('ship') || t.includes('vessel') || t.includes('freight')) cat = 'Tankers';
          else if (t.includes('inventor') || t.includes('eia') || t.includes('stock') || t.includes('draw') || t.includes('build')) cat = 'Inventories';
          else if (t.includes('refiner') || t.includes('crack') || t.includes('gasoline') || t.includes('distillate')) cat = 'Refineries';
          else if (t.includes('war') || t.includes('houthi') || t.includes('iran') || t.includes('russia') || t.includes('gaza') || t.includes('ukraine') || t.includes('geopolitic')) cat = 'Geopolitics';
          
          return {
              id: item.url || index.toString(),
              headline: item.title,
              source: item.source,
              category: cat,
              sentiment: 'neutral', // default
              timestamp: new Date(item.published_at).getTime(),
              impactScore: 5, // default
              pinned: false,
              summary: item.summary,
              url: item.url
          };
      });
      
      set({ newsItems: mappedNews, isLoadingNews: false });
    } catch (err) {
      console.error(err);
      set({ newsError: err.message, isLoadingNews: false });
    }
  }
}));

export default useNewsStore;
