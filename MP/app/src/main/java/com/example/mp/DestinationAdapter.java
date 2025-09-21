package com.example.mp;

import android.util.Pair;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class DestinationAdapter extends RecyclerView.Adapter<DestinationAdapter.ViewHolder> {

    private final List<Pair<String, String>> destinations;
    private int selectedPosition = 0; // Start with the first item selected

    public DestinationAdapter(List<Pair<String, String>> destinations) {
        this.destinations = destinations;
    }

    public void setSelectedPosition(int position) {
        this.selectedPosition = position;
        notifyDataSetChanged(); // Redraw the list to show the new highlight
    }

    public int getSelectedPosition() {
        return selectedPosition;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.list_item_destination, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        Pair<String, String> destination = destinations.get(position);
        holder.bind(destination, position == selectedPosition);
    }

    @Override
    public int getItemCount() {
        return destinations.size();
    }

    static class ViewHolder extends RecyclerView.ViewHolder {
        private final TextView textView;

        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            textView = itemView.findViewById(R.id.textViewDestinationName);
        }

        public void bind(final Pair<String, String> destination, boolean isSelected) {
            String locationName = destination.second;
            textView.setText(locationName);
            // This will trigger the color change from our selector drawable
            itemView.setActivated(isSelected);
        }
    }
}