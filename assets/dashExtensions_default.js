window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, context) {
            const props = context && context.props ? context.props : {};
            const hideout = context.hideout || {};
            const highlight_id = hideout.highlight_id;
            const isHighlighted = feature.properties.hwycovid == highlight_id;

            if (isHighlighted) {
                return {
                    color: "yellow",
                    weight: 6,
                    opacity: 1.0
                };
            }

            const gap = feature.properties.gap_day;
            let color = 'gray';

            if (gap !== null && gap !== undefined) {
                if (gap < -10) {
                    color = '#08306b';
                } else if (gap < -5) {
                    color = '#2171b5';
                } else if (gap < 0) {
                    color = '#6baed6';
                } else if (gap < 5) {
                    color = '#fc9272';
                } else if (gap < 10) {
                    color = '#fb6a4a';
                } else {
                    color = '#cb181d';
                }
            }

            if (isHighlighted) {
                return {
                    color: 'yellow',
                    weight: 6,
                    opacity: 1.0
                };
            }

            return {
                color: color,
                weight: 3,
                opacity: 0.7
            };
        }
    }
});