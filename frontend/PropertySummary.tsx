import { Home, Maximize2, Calendar, Zap, MapPin, Key } from "lucide-react";
import type { Property } from "@/lib/types";
import {
  formatPropertyType, formatFloorArea, formatTenure,
  formatDate, epcColor,
} from "@/lib/formatters";
import { Card, SectionHeader, StatRow, Badge } from "@/components/ui";

interface Props { property: Property; }

function AttributeChip({ icon: Icon, label, value }: {
  icon: React.ElementType; label: string; value: string;
}) {
  return (
    <div className="flex items-center gap-3 bg-surface-raised rounded-xl p-3.5">
      <div className="w-8 h-8 rounded-lg bg-stone-200/60 flex items-center justify-center shrink-0">
        <Icon size={15} className="text-ink-muted" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-ink-faint">{label}</p>
        <p className="text-sm font-medium text-ink truncate">{value}</p>
      </div>
    </div>
  );
}

export function PropertySummary({ property }: Props) {
  const { address } = property;

  const fullAddress = [
    address.line_1,
    address.line_2,
    address.city,
    address.county,
  ].filter(Boolean).join(", ");

  const attributes = [
    {
      icon: Home,
      label: "Type",
      value: formatPropertyType(property.property_type),
    },
    {
      icon: Maximize2,
      label: "Floor area",
      value: formatFloorArea(property.floor_area_m2),
    },
    {
      icon: Calendar,
      label: "Year built",
      value: property.year_built ? String(property.year_built) : "N/A",
    },
    {
      icon: Key,
      label: "Tenure",
      value: formatTenure(property.tenure),
    },
  ];

  return (
    <Card>
      <SectionHeader
        title="Property details"
        action={
          property.epc_rating ? (
            <span className={`text-xs font-mono font-bold px-3 py-1.5 rounded-lg ${epcColor(property.epc_rating)}`}>
              EPC {property.epc_rating}
            </span>
          ) : undefined
        }
      />

      {/* Address block */}
      <div className="flex items-start gap-3 mb-6 pb-6 border-b border-stone-50">
        <div className="w-9 h-9 rounded-xl bg-gold-300/20 flex items-center justify-center shrink-0 mt-0.5">
          <MapPin size={16} className="text-gold-500" />
        </div>
        <div>
          <p className="font-medium text-ink leading-snug">{fullAddress}</p>
          <p className="font-mono text-sm text-ink-muted mt-0.5">{address.postcode}</p>
        </div>
      </div>

      {/* Bedroom / bathroom pills */}
      <div className="flex gap-3 mb-6">
        {property.bedrooms != null && (
          <div className="flex items-center gap-1.5 text-sm text-ink-muted bg-stone-50 border border-stone-100 rounded-full px-3 py-1.5">
            <span className="text-base">🛏</span>
            <span><strong className="text-ink">{property.bedrooms}</strong> bed{property.bedrooms !== 1 ? "s" : ""}</span>
          </div>
        )}
        {property.bathrooms != null && (
          <div className="flex items-center gap-1.5 text-sm text-ink-muted bg-stone-50 border border-stone-100 rounded-full px-3 py-1.5">
            <span className="text-base">🚿</span>
            <span><strong className="text-ink">{property.bathrooms}</strong> bath{property.bathrooms !== 1 ? "s" : ""}</span>
          </div>
        )}
        {property.is_new_build && (
          <Badge variant="gold">New build</Badge>
        )}
      </div>

      {/* Attribute grid */}
      <div className="grid grid-cols-2 gap-3">
        {attributes.map((a) => (
          <AttributeChip key={a.label} {...a} />
        ))}
      </div>

      {/* Council tax band */}
      {property.council_tax_band && (
        <div className="mt-4 pt-4 border-t border-stone-50">
          <StatRow
            label="Council tax band"
            value={<span className="font-mono">Band {property.council_tax_band}</span>}
          />
        </div>
      )}
    </Card>
  );
}
