import { useState } from 'react';
import type { Campaign, Publisher } from '../pages/Dashboard';

interface SidebarProps {
  campaigns: Campaign[];
  selected: Publisher;
  onSelect: (publisher: Publisher) => void;
}

function Sidebar({ campaigns, selected, onSelect }: SidebarProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    () => Object.fromEntries(campaigns.map((c) => [c.name, true]))
  );

  const toggleCampaign = (name: string) => {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-title">Campaigns</div>
      <hr className="sidebar-divider" />
      {campaigns.map((campaign) => (
        <div key={campaign.name} className="campaign-group">
          <button
            className="campaign-header"
            onClick={() => toggleCampaign(campaign.name)}
          >
            <span className={`campaign-chevron ${expanded[campaign.name] ? 'open' : ''}`}>
              &#9656;
            </span>
            {campaign.name}
          </button>
          {expanded[campaign.name] && (
            <div className="campaign-publishers">
              {campaign.publishers.map((pub) => (
                <button
                  key={pub.name}
                  className={`sidebar-btn ${selected === pub ? 'active' : ''}`}
                  onClick={() => onSelect(pub)}
                >
                  {selected === pub ? '> ' : ''}{pub.name}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </aside>
  );
}

export default Sidebar;
